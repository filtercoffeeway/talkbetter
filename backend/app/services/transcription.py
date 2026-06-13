"""Phase 1 — Speech-to-text with faster-whisper (local, no API key).

Returns a Transcript with word-level timestamps, which Phase 1's pace/pause
logic and Phase 3's alignment both depend on.

IMPLEMENTATION NOTES (for the dev session):
  - Lazy-load the WhisperModel once at module level (model load is slow).
    Use settings.whisper_model / whisper_device / whisper_compute_type.
  - faster-whisper accepts a file path or file-like object. Browser audio
    usually arrives as webm/opus; ffmpeg (bundled via faster-whisper's
    av dependency) decodes it. Write bytes to a temp file if needed.
  - Call model.transcribe(path, word_timestamps=True). Iterate segments,
    then segment.words to build WordTiming list. duration_sec = info.duration.
"""
from app.models.schemas import Transcript


def transcribe(audio_bytes: bytes, filename: str | None = None) -> Transcript:
    """Transcribe audio bytes to text + word timings.

    TODO(Phase 1): implement with faster-whisper. Replace the stub below.
    """
    raise NotImplementedError(
        "Implement faster-whisper transcription. See docstring + docs/spec.html (Phase 1)."
    )
