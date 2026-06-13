"""Phase 3 — American-accent scoring via Azure Pronunciation Assessment."""
from __future__ import annotations

import subprocess
import tempfile
from pathlib import Path

from app.config import settings
from app.models.schemas import AccentReport, PhonemeScore, WordPronunciation

_ACCURACY_THRESHOLD = 60.0


def _to_wav_16k(audio_bytes: bytes, src_suffix: str) -> bytes:
    """Transcode arbitrary audio to 16kHz mono PCM WAV using ffmpeg."""
    with (
        tempfile.NamedTemporaryFile(suffix=src_suffix, delete=False) as src,
        tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as dst,
    ):
        src.write(audio_bytes)
        src_path, dst_path = src.name, dst.name

    try:
        subprocess.run(
            [
                "ffmpeg", "-y", "-i", src_path,
                "-ar", "16000", "-ac", "1",
                "-f", "wav", dst_path,
            ],
            check=True,
            capture_output=True,
        )
        return Path(dst_path).read_bytes()
    finally:
        Path(src_path).unlink(missing_ok=True)
        Path(dst_path).unlink(missing_ok=True)


def assess(audio_bytes: bytes, reference_text: str, src_suffix: str = ".webm") -> AccentReport:
    """Score pronunciation of audio against the reference sentence via Azure."""
    import azure.cognitiveservices.speech as speechsdk

    wav_bytes = _to_wav_16k(audio_bytes, src_suffix)

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
        pa = pron_result.pronunciation_assessment

        problem_words: list[WordPronunciation] = []
        for word in pron_result.words:
            wa = word.pronunciation_assessment
            phonemes = [
                PhonemeScore(phoneme=p.phoneme, accuracy=p.pronunciation_assessment.accuracy_score)
                for p in (word.phonemes or [])
            ]
            if wa.accuracy_score < _ACCURACY_THRESHOLD or wa.error_type not in (None, "None", ""):
                problem_words.append(
                    WordPronunciation(
                        word=word.word,
                        accuracy=wa.accuracy_score,
                        error_type=wa.error_type if wa.error_type not in (None, "None", "") else None,
                        phonemes=phonemes,
                    )
                )

        return AccentReport(
            accuracy_score=pa["AccuracyScore"],
            fluency_score=pa["FluencyScore"],
            completeness_score=pa["CompletenessScore"],
            pron_score=pa["PronScore"],
            problem_words=problem_words,
        )
    finally:
        Path(wav_path).unlink(missing_ok=True)
