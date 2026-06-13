"""Phase 3 — American-accent scoring via Azure Pronunciation Assessment.

This is the only realistic way to get phoneme-level accent feedback without
training models yourself. Requires AZURE_SPEECH_KEY + AZURE_SPEECH_REGION.

Accent scoring is REFERENCE-BASED: the user reads a known sentence
(`reference_text`) and Azure scores how closely their pronunciation matches.
So Phase 3 needs a "read this sentence" practice mode in the UI, distinct from
the free-speech mode used in Phases 1-2.

IMPLEMENTATION NOTES (for the dev session):
  - Use azure.cognitiveservices.speech with PronunciationAssessmentConfig
    (reference_text, GradingSystem.HundredMark, Granularity.Phoneme,
     enable_miscue=True).
  - Azure wants 16kHz mono PCM WAV. Browser audio is webm/opus, so transcode
    with ffmpeg before sending.
  - From the result JSON, pull NBest[0].PronunciationAssessment
    (AccuracyScore, FluencyScore, CompletenessScore, PronScore) and per-word
    + per-phoneme scores. Surface words below an accuracy threshold (e.g. <60)
    as problem_words.
"""
from app.config import settings
from app.models.schemas import AccentReport


def assess(audio_bytes: bytes, reference_text: str) -> AccentReport:
    """Score pronunciation of audio against the reference sentence.

    TODO(Phase 3): implement with Azure Speech SDK.
    """
    raise NotImplementedError(
        "Implement Azure pronunciation assessment. See docstring + docs/spec.html (Phase 3)."
    )
