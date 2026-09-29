"""Phase 3 — American-accent scoring via Azure Pronunciation Assessment.

Selected with PRONUNCIATION_PROVIDER=azure; needs AZURE_SPEECH_KEY/REGION.
"""
from __future__ import annotations

import tempfile
from pathlib import Path

from app.config import settings
from app.models.schemas import AccentReport, PhonemeScore, WordPronunciation
from app.services.audio import to_wav_16k

_ACCURACY_THRESHOLD = 60.0


def assess(audio_bytes: bytes, reference_text: str, src_suffix: str = ".webm") -> AccentReport:
    """Score pronunciation of audio against the reference sentence via Azure."""
    import azure.cognitiveservices.speech as speechsdk

    wav_bytes = to_wav_16k(audio_bytes, src_suffix)

    speech_config = speechsdk.SpeechConfig(
        subscription=settings.azure_speech_key,
        region=settings.azure_speech_region,
    )

    pron_config = speechsdk.PronunciationAssessmentConfig(
        reference_text=reference_text,
        grading_system=speechsdk.PronunciationAssessmentGradingSystem.HundredMark,
        granularity=speechsdk.PronunciationAssessmentGranularity.Phoneme,
        enable_miscue=True,
    )

    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
        tmp.write(wav_bytes)
        wav_path = tmp.name

    try:
        audio_cfg = speechsdk.audio.AudioConfig(filename=wav_path)
        recognizer = speechsdk.SpeechRecognizer(
            speech_config=speech_config,
            audio_config=audio_cfg,
        )
        pron_config.apply_to(recognizer)

        result = recognizer.recognize_once_async().get()

        if result.reason != speechsdk.ResultReason.RecognizedSpeech:
            raise RuntimeError(f"Azure recognition failed: {result.reason}")

        pron_result = speechsdk.PronunciationAssessmentResult(result)

        # The SDK only sets `words` / `phonemes` / `error_type` when Azure's JSON
        # includes them (e.g. an omitted word has no phonemes), and the property
        # getters raise AttributeError otherwise — hence the getattr defaults.
        problem_words: list[WordPronunciation] = []
        for word in getattr(pron_result, "words", None) or []:
            accuracy = getattr(word, "accuracy_score", 0.0)
            error_type = getattr(word, "error_type", None)
            if error_type in ("None", ""):
                error_type = None
            phonemes = [
                PhonemeScore(phoneme=p.phoneme, accuracy=p.accuracy_score)
                for p in (getattr(word, "phonemes", None) or [])
            ]
            if accuracy < _ACCURACY_THRESHOLD or error_type is not None:
                problem_words.append(
                    WordPronunciation(
                        word=word.word,
                        accuracy=accuracy,
                        error_type=error_type,
                        phonemes=phonemes,
                    )
                )

        return AccentReport(
            accuracy_score=pron_result.accuracy_score,
            fluency_score=pron_result.fluency_score,
            completeness_score=pron_result.completeness_score,
            pron_score=pron_result.pronunciation_score,
            problem_words=problem_words,
        )
    finally:
        Path(wav_path).unlink(missing_ok=True)
