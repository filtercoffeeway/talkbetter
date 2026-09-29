"""TalkBetter FastAPI entrypoint.

Run (from backend/):
    uvicorn app.main:app --reload
"""
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.db import init_db
from app.routers import analysis, history, profiles, program
from app.services import pronunciation


@asynccontextmanager
async def lifespan(_app: FastAPI):
    init_db()
    llm_key = settings.anthropic_api_key if settings.llm_provider == "anthropic" else settings.openai_api_key
    print(f"  Phase 1 (transcription/pace):  ON  [whisper={settings.whisper_model}]")
    print(f"  Phase 2 (grammar/clarity LLM): {'ON ' if llm_key else 'OFF — set ANTHROPIC_API_KEY in backend/.env'}")
    accent_off_hint = (
        "set AZURE_SPEECH_KEY/REGION in backend/.env"
        if settings.pronunciation_provider == "azure"
        else "install espeak-ng (and ffmpeg)"
    )
    label = f"Phase 3 (accent/{settings.pronunciation_provider}):".ljust(31)
    print(f"  {label}{'ON ' if pronunciation.is_available() else 'OFF — ' + accent_off_hint}")
    yield


app = FastAPI(title="TalkBetter API", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(analysis.router, prefix="/api")
app.include_router(profiles.router, prefix="/api")
app.include_router(history.router, prefix="/api")
app.include_router(program.router, prefix="/api")


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok"}
