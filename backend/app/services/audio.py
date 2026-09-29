"""Audio transcoding helpers (ffmpeg must be on the host)."""
from __future__ import annotations

import subprocess
import tempfile
from pathlib import Path

import numpy as np

SAMPLE_RATE = 16_000


def _ffmpeg(audio_bytes: bytes, src_suffix: str, out_suffix: str, out_args: list[str]) -> bytes:
    """Transcode the input bytes to 16kHz mono with ffmpeg and return the output bytes.

    Output goes to a real file (not stdout) so WAV headers get correct sizes.
    """
    with (
        tempfile.NamedTemporaryFile(suffix=src_suffix, delete=False) as src,
        tempfile.NamedTemporaryFile(suffix=out_suffix, delete=False) as dst,
    ):
        src.write(audio_bytes)
        src_path, dst_path = src.name, dst.name

    try:
        subprocess.run(
            [
                "ffmpeg", "-y", "-i", src_path,
                "-ar", str(SAMPLE_RATE), "-ac", "1",
                *out_args, dst_path,
            ],
            check=True,
            capture_output=True,
        )
        return Path(dst_path).read_bytes()
    finally:
        Path(src_path).unlink(missing_ok=True)
        Path(dst_path).unlink(missing_ok=True)


def to_wav_16k(audio_bytes: bytes, src_suffix: str) -> bytes:
    """Transcode arbitrary audio to 16kHz mono PCM WAV bytes."""
    return _ffmpeg(audio_bytes, src_suffix, ".wav", ["-f", "wav"])


def to_pcm_16k(audio_bytes: bytes, src_suffix: str) -> np.ndarray:
    """Decode arbitrary audio to a 16kHz mono float32 waveform in [-1, 1]."""
    raw = _ffmpeg(audio_bytes, src_suffix, ".raw", ["-f", "f32le"])
    return np.frombuffer(raw, dtype=np.float32)
