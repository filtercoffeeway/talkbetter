"""Optional archive of accent-practice recordings (SAVE_RECORDINGS=true).

Each upload is stored as `<timestamp>_<label or "accent">.<ext>` next to a
`.txt` holding the reference sentence (label = program day +
activity), so recordings can be replayed or re-scored later (see scripts/compare_providers.py). data/recordings/ is
gitignored.
"""
from __future__ import annotations

from datetime import datetime
from pathlib import Path

from app.config import settings


def save(audio_bytes: bytes, suffix: str, reference_text: str, label: str | None) -> Path:
    """Write the audio and its reference sentence; returns the audio path."""
    folder = settings.recordings_dir
    folder.mkdir(parents=True, exist_ok=True)
    stem = f"{datetime.now():%Y%m%d-%H%M%S-%f}_{label or 'accent'}"
    path = folder / f"{stem}{suffix or '.webm'}"
    path.write_bytes(audio_bytes)
    path.with_suffix(".txt").write_text(reference_text, encoding="utf-8")
    return path
