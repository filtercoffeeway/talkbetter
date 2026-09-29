"""Application settings, loaded from environment / .env.

See .env.example for all variables. Phase 1 requires none of the API keys.
"""
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# Repo root = two levels up from this file (backend/app/config.py -> repo/).
_REPO_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # App
    app_host: str = "127.0.0.1"
    app_port: int = 8000
    cors_origins: str = "http://localhost:5173"

    # Persistence (Phase 4). Override with DB_PATH in .env if desired.
    db_path: Path = _REPO_ROOT / "data" / "talkbetter.db"
    # Keep accent-practice audio (+ its sentence) for replay / provider comparison.
    save_recordings: bool = False
    recordings_dir: Path = _REPO_ROOT / "data" / "recordings"

    # Whisper (Phase 1)
    whisper_model: str = "small"
    whisper_device: str = "cpu"
    whisper_compute_type: str = "int8"

    # LLM (Phase 2)
    llm_provider: str = "anthropic"          # "anthropic" | "openai"
    anthropic_api_key: str = ""
    anthropic_model: str = "claude-sonnet-5-5"
    openai_api_key: str = ""
    openai_model: str = "gpt-4o"

    # Pronunciation / accent (Phase 3)
    pronunciation_provider: str = "local"    # "local" | "azure"
    # Local provider: wav2vec2 CTC model emitting espeak IPA phonemes
    pronunciation_model: str = "facebook/wav2vec2-lv-60-espeak-cv-ft"
    espeak_voice: str = "en-us"              # reference pronunciation (American)
    azure_speech_key: str = ""
    azure_speech_region: str = ""

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


settings = Settings()
