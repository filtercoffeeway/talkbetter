"""Progress/history endpoint (Phase 4).

  GET /api/history?profile_id=<id>  -> that profile's sessions (newest first)
                                        plus the current practice streak.

Drives the frontend dashboard charts and streak counter.
"""
from fastapi import APIRouter, HTTPException, Query

from app.models.schemas import HistoryResponse
from app.services import storage

router = APIRouter()


@router.get("/history", response_model=HistoryResponse)
def get_history(
    profile_id: int = Query(..., description="Profile to fetch history for"),
    limit: int = Query(100, ge=1, le=500),
) -> HistoryResponse:
    if not storage.profile_exists(profile_id):
        raise HTTPException(status_code=404, detail="Profile not found.")
    return storage.list_history(profile_id, limit=limit)
