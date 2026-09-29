"""Phase 3 — American-accent scoring, dispatched by PRONUNCIATION_PROVIDER.

  local -> pronunciation_local  (wav2vec2 phoneme model + espeak-ng; no key)
  azure -> pronunciation_azure  (Azure Pronunciation Assessment; needs a key)

Both return the same AccentReport, so switching is a config change only.
"""
from __future__ import annotations

import importlib.util
import shutil

from app.config import settings
from app.models.schemas import AccentReport


def is_available() -> bool:
    """True when the configured provider has what it needs to run.

    Used by the router to skip Phase 3 gracefully instead of erroring.
    """
    provider = settings.pronunciation_provider
    if provider == "azure":
        return bool(settings.azure_speech_key and settings.azure_speech_region)
    if provider == "local":
        return (
            importlib.util.find_spec("torch") is not None
            and importlib.util.find_spec("transformers") is not None
            and shutil.which("espeak-ng") is not None
        )
    return False


def assess(audio_bytes: bytes, reference_text: str, src_suffix: str = ".webm") -> AccentReport:
    """Score pronunciation of `audio_bytes` against `reference_text`."""
    provider = settings.pronunciation_provider
    if provider == "azure":
        from app.services import pronunciation_azure as impl
    elif provider == "local":
        from app.services import pronunciation_local as impl
    else:
        raise ValueError(f"Unknown PRONUNCIATION_PROVIDER: {provider!r}")
    return impl.assess(audio_bytes, reference_text, src_suffix)
