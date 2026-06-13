"""Profile endpoints (Phase 4).

Local, trusted, multi-person app: profiles are just named buckets for keeping
each person's practice history separate. No auth/passwords by design.

  GET  /api/profiles        -> list all profiles (with session counts)
  POST /api/profiles        -> create (or get existing) by name
"""
from fastapi import APIRouter, HTTPException

from app.models.schemas import Profile, ProfileCreate
from app.services import storage

router = APIRouter()


@router.get("/profiles", response_model=list[Profile])
def get_profiles() -> list[Profile]:
    return storage.list_profiles()


@router.post("/profiles", response_model=Profile, status_code=201)
def post_profile(body: ProfileCreate) -> Profile:
    try:
        return storage.create_profile(body.name)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
