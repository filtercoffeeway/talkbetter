"""POST /api/analyze — the core endpoint.

Accepts an uploaded audio clip (and an optional reference script for accent
scoring) and returns an AnalysisResponse. Orchestrates the service layer.

Build order (see docs/spec.html):
  Phase 1 -> transcription + pace_fillers
  Phase 2 -> language (grammar + clarity)
  Phase 3 -> accent (requires `reference_text`)
"""
from pathlib import Path

from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from app.config import settings
from app.models.schemas import AnalysisResponse
from app.services import (
    course,
    filler_pace,
    llm_feedback,
    pronunciation,
    storage,
    transcription,
)

router = APIRouter()


@router.post("/analyze", response_model=AnalysisResponse)
async def analyze(
    audio: UploadFile = File(...),
    reference_text: str | None = Form(None),   # used by Phase 3 accent scoring
    profile_id: int | None = Form(None),       # Phase 4: persist under this profile
    lesson_id: str | None = Form(None),        # Phase 4: practicing a course lesson
) -> AnalysisResponse:
    audio_bytes = await audio.read()

    # --- Phase 1 ---
    transcript = transcription.transcribe(audio_bytes, filename=audio.filename)
    pace = filler_pace.analyze(transcript)

    response = AnalysisResponse(transcript=transcript, pace_fillers=pace)

    # --- Phase 2 (skipped if no LLM key is configured) ---
    llm_key = (
        settings.anthropic_api_key
        if settings.llm_provider == "anthropic"
        else settings.openai_api_key
    )
    if transcript.text.strip() and llm_key:
        response.language = llm_feedback.analyze(transcript.text)

    # --- Phase 3 (skipped if no Azure key or no reference text) ---
    if reference_text and settings.azure_speech_key:
        src_suffix = Path(audio.filename).suffix if audio.filename else ".webm"
        response.accent = pronunciation.assess(audio_bytes, reference_text, src_suffix)

    # --- Phase 4: persist the session for progress tracking ---
    # Optional: free-standing one-off analyses (no profile) still work.
    if profile_id is not None:
        if not storage.profile_exists(profile_id):
            raise HTTPException(status_code=404, detail="Profile not found.")
        mode = "accent" if reference_text else "free"
        response.session_id = storage.save_session(profile_id, mode, response)

        # If this was an accent-course lesson, advance that lesson's progress.
        # We key off the lesson's pronunciation score (None when Phase 3 isn't
        # configured — the attempt still counts, it just can't "complete").
        if lesson_id is not None:
            if course.get_lesson(lesson_id) is None:
                raise HTTPException(status_code=404, detail="Lesson not found.")
            score = response.accent.pron_score if response.accent else None
            storage.record_lesson_attempt(
                profile_id, lesson_id, score, course.TARGET_SCORE
            )

    return response
