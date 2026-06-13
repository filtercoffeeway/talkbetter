"""POST /api/analyze — the core endpoint.

Accepts an uploaded audio clip (and an optional reference script for accent
scoring) and returns an AnalysisResponse. Orchestrates the service layer.

Build order (see docs/spec.html):
  Phase 1 -> transcription + pace_fillers
  Phase 2 -> language (grammar + clarity)
  Phase 3 -> accent (requires `reference_text`)
"""
from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from app.models.schemas import AnalysisResponse
from app.services import filler_pace, storage, transcription
# from app.services import llm_feedback      # Phase 2
# from app.services import pronunciation     # Phase 3

router = APIRouter()


@router.post("/analyze", response_model=AnalysisResponse)
async def analyze(
    audio: UploadFile = File(...),
    reference_text: str | None = Form(None),   # used by Phase 3 accent scoring
    profile_id: int | None = Form(None),       # Phase 4: persist under this profile
) -> AnalysisResponse:
    audio_bytes = await audio.read()

    # --- Phase 1 ---
    transcript = transcription.transcribe(audio_bytes, filename=audio.filename)
    pace = filler_pace.analyze(transcript)

    response = AnalysisResponse(transcript=transcript, pace_fillers=pace)

    # --- Phase 2 (uncomment when implemented) ---
    # response.language = llm_feedback.analyze(transcript.text)

    # --- Phase 3 (uncomment when implemented) ---
    # if reference_text:
    #     response.accent = pronunciation.assess(audio_bytes, reference_text)

    # --- Phase 4: persist the session for progress tracking ---
    # Optional: free-standing one-off analyses (no profile) still work.
    if profile_id is not None:
        if not storage.profile_exists(profile_id):
            raise HTTPException(status_code=404, detail="Profile not found.")
        mode = "accent" if reference_text else "free"
        response.session_id = storage.save_session(profile_id, mode, response)

    return response
