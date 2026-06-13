"""TalkBetter FastAPI entrypoint.

Run (from backend/):
    uvicorn app.main:app --reload

The /api/analyze endpoint is the core of the app. See docs/spec.html for the
full contract and the phase-by-phase build plan.
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.db import init_db
from app.routers import analysis, history, profiles

app = FastAPI(title="TalkBetter API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def _startup() -> None:
    # Create the SQLite tables if they don't exist yet (Phase 4).
    init_db()


app.include_router(analysis.router, prefix="/api")
app.include_router(profiles.router, prefix="/api")
app.include_router(history.router, prefix="/api")


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok"}
