"""30-day program endpoints.

  GET /api/program                           -> the curriculum (every day open, no progress)
  GET /api/program?profile_id=<id>           -> curriculum + that profile's activity results,
                                                day statuses and a summary
  GET /api/program/benchmarks?profile_id=<id>-> the daily benchmark trend (per day + per week)

Attempts are recorded as a side effect of POST /api/analyze with
``program_day`` + ``activity_id``.
"""
from fastapi import APIRouter, HTTPException, Query

from app.models.schemas import BenchmarkHistory, ProgramResponse
from app.services import program, storage

router = APIRouter()


def _check_profile(profile_id: int) -> None:
    if not storage.profile_exists(profile_id):
        raise HTTPException(status_code=404, detail="Profile not found.")


@router.get("/program", response_model=ProgramResponse)
def get_program(
    profile_id: int | None = Query(None, description="Overlay this profile's progress, if given"),
) -> ProgramResponse:
    if profile_id is not None:
        _check_profile(profile_id)
    return program.get_program(profile_id)


@router.get("/program/benchmarks", response_model=BenchmarkHistory)
def get_benchmarks(profile_id: int = Query(...)) -> BenchmarkHistory:
    _check_profile(profile_id)
    return program.get_benchmarks(profile_id)
