"""POST /api/analyze — the core endpoint.

Accepts an uploaded audio clip (and an optional reference script for accent
scoring) and returns an AnalysisResponse. Orchestrates the service layer.

Build order (see docs/spec.html):
  Phase 1 -> transcription + pace_fillers
  Phase 2 -> language (grammar + clarity)
  Phase 3 -> accent (requires `reference_text`)
  30-day program -> `program_day` + `activity_id` score the recording against
                    that day's activity (and the daily benchmark)
"""
from pathlib import Path

from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from app.config import settings
from app.models.schemas import AnalysisResponse
from app.services import (
    filler_pace,
    llm_feedback,
    program,
    pronunciation,
    recordings,
    storage,
    transcription,
)

router = APIRouter()


@router.post("/analyze", response_model=AnalysisResponse)
async def analyze(
    audio: UploadFile = File(...),
    reference_text: str | None = Form(None),   # used by Phase 3 accent scoring
    profile_id: int | None = Form(None),       # Phase 4: persist under this profile
    program_day: int | None = Form(None),      # 30-day program: which day (1-30) …
    activity_id: str | None = Form(None),      # … and which of its activities
) -> AnalysisResponse:
    # The program's content is authoritative: a read activity always scores its
    # own sentence, so the benchmark passage can't drift.
    activity = None
    if program_day is not None or activity_id is not None:
        if profile_id is None:
            raise HTTPException(status_code=400, detail="Program activities need a profile_id.")
        activity = program.get_activity(program_day or 0, activity_id or "")
        if activity is None:
            raise HTTPException(status_code=404, detail="Program activity not found.")
        reference_text = activity.reference_text

    audio_bytes = await audio.read()

    # --- Phase 1 ---
    transcript = transcription.transcribe(audio_bytes, filename=audio.filename)
    pace = filler_pace.analyze(transcript)

    response = AnalysisResponse(transcript=transcript, pace_fillers=pace)

    # --- Phase 2 (skipped if no LLM key is configured) ---
    # Not for read-aloud: the words come from a script, so grammar says nothing
    # about the speaker — accent scoring (Phase 3) judges whether they were said right.
    if transcript.text.strip() and not reference_text and llm_feedback.is_available():
        response.language = llm_feedback.analyze(transcript.text)
        # Open-ended program answers also get the confidence/structure rubric.
        if activity is not None and activity.kind == "speak":
            response.speaking = llm_feedback.assess_speaking(
                transcript.text, activity.prompt, pace
            )

    # --- Phase 3 (skipped if no reference text or the provider isn't set up) ---
    src_suffix = Path(audio.filename).suffix if audio.filename else ".webm"
    if reference_text and settings.save_recordings:
        label = f"day{program_day:02d}-{activity_id}" if activity else None
        recordings.save(audio_bytes, src_suffix, reference_text, label)
    if reference_text and pronunciation.is_available():
        response.accent = pronunciation.assess(audio_bytes, reference_text, src_suffix)

    # --- Phase 4: persist the session for progress tracking ---
    # Optional: free-standing one-off analyses (no profile) still work.
    if profile_id is not None:
        if not storage.profile_exists(profile_id):
            raise HTTPException(status_code=404, detail="Profile not found.")
        mode = "accent" if reference_text else "free"
        response.session_id = storage.save_session(profile_id, mode, response)

        if activity is not None:
            response.program = program.record_attempt(
                profile_id, program_day, activity, response, response.session_id
            )

    return response
