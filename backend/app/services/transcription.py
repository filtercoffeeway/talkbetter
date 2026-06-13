"""Phase 1 — Speech-to-text with faster-whisper (local, no API key)."""
from __future__ import annotations

import tempfile
from pathlib import Path

from faster_whisper import WhisperModel

from app.config import settings
from app.models.schemas import Transcript, WordTiming

_model: WhisperModel | None = None


def _get_model() -> WhisperModel:
    global _model
    if _model is None:
        _model = WhisperModel(
            settings.whisper_model,
            device=settings.whisper_device,
            compute_type=settings.whisper_compute_type,
        )
    return _model


def transcribe(audio_bytes: bytes, filename: str | None = None) -> Transcript:
    """Transcribe audio bytes to text + word timings via faster-whisper."""
    suffix = Path(filename).suffix if filename else ".webm"
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        tmp.write(audio_bytes)
        tmp_path = tmp.name

    try:
        model = _get_model()
        segments, info = model.transcribe(
            tmp_path,
            word_timestamps=True,
            vad_filter=True,
        )
        words: list[WordTiming] = []
        text_parts: list[str] = []
        for seg in segments:
            text_parts.append(seg.text.strip())
            if seg.words:
                for w in seg.words:
                    words.append(WordTiming(word=w.word.strip(), start=w.start, end=w.end))
    finally:
        Path(tmp_path).unlink(missing_ok=True)

    return Transcript(
        text=" ".join(text_parts),
        words=words,
        duration_sec=info.duration,
    )
