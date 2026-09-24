"""American-accent course endpoint (Phase 4).

  GET /api/course                     -> the static curriculum (no progress)
  GET /api/course?profile_id=<id>     -> the curriculum with that profile's
                                         per-lesson progress + a completion summary

The curriculum content lives in services/course.py; per-profile progress is in
SQLite (lesson_progress). Progress itself is recorded as a side effect of
practicing a lesson via POST /api/analyze (pass ``lesson_id``).
"""
from fastapi import APIRouter, HTTPException, Query

from app.models.schemas import CourseResponse
from app.services import course, storage

router = APIRouter()


@router.get("/course", response_model=CourseResponse)
def get_course(
    profile_id: int | None = Query(
        None, description="Overlay this profile's progress, if given"
    ),
) -> CourseResponse:
    if profile_id is not None and not storage.profile_exists(profile_id):
        raise HTTPException(status_code=404, detail="Profile not found.")
    return course.get_course(profile_id)
