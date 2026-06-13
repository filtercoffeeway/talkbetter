# TalkBetter — Context for AI coding sessions

Read this first, then read `docs/spec.html` (open it in a browser — it's the
authoritative, detailed build spec). This file is the quick orientation.

## What this is
A **local** app that helps a non-native English speaker (the owner, Mahesh)
improve spoken English along four axes: **filler words, speaking pace, grammar,
clarity, and American accent**. Audio is captured in the browser and analyzed by
a Python backend. It runs on the user's own machine.

## Current status
**Scaffolded, not yet implemented.** The structure, config, API contract, and
stub modules exist. Every service module raises `NotImplementedError` with a
docstring describing what to build. Implement in phase order.

## Tech stack
- **Frontend:** React + Vite (`frontend/`). Mic capture via browser `MediaRecorder`.
- **Backend:** FastAPI + Uvicorn (`backend/`).
- **Transcription:** `faster-whisper` (local, no key) — Phase 1.
- **Grammar/clarity:** LLM, default **Claude** (`LLM_PROVIDER=anthropic`), OpenAI swappable — Phase 2.
- **Accent:** **Azure Pronunciation Assessment** — Phase 3.
- **ffmpeg** must be on the host for audio transcode.

## Build phases (do in order; each has acceptance criteria in spec.html)
1. **Phase 1 — Transcription + pace + fillers.** Local, no API keys. First working loop.
2. **Phase 2 — Grammar + clarity.** Needs an LLM key.
3. **Phase 3 — American accent.** Needs Azure key; reference-based (user reads a sentence).
4. **Phase 4 — Progress tracking & polish.** Optional; SQLite history + charts.

## Where things live
- API contract / response shapes: `backend/app/models/schemas.py` (single source of truth).
- Endpoint orchestration: `backend/app/routers/analysis.py` (`POST /api/analyze`).
- Service stubs to implement: `backend/app/services/{transcription,filler_pace,llm_feedback,pronunciation}.py`.
- Config (reads `.env`): `backend/app/config.py`; template in `backend/.env.example`.
- Frontend entry: `frontend/src/App.jsx` (has both "free speaking" and "accent practice" modes).
- **Phase 4 (built): profiles + progress.** SQLite layer `backend/app/db.py` (stdlib `sqlite3`, DB at
  `data/talkbetter.db`, gitignored); persistence/queries `backend/app/services/storage.py`; endpoints
  `backend/app/routers/{profiles,history}.py` (`GET/POST /api/profiles`, `GET /api/history`).
  Frontend: `ProfilePicker.jsx` (name-only, no auth) + `Dashboard.jsx` (Chart.js trends + streak).
  `/api/analyze` takes an optional `profile_id` form field; when present the session is saved and the
  response includes `session_id`. Persistence works even before Phases 1–3 land (metrics nullable).

## Conventions
- Keep `schemas.py` and the API section of `docs/spec.html` in sync — the frontend trusts those field names.
- Later-phase fields (`language`, `accent`) are nullable; the frontend renders only present sections,
  so a partially-built backend still works end to end.
- Don't commit `.env` or anything under `data/recordings/` (already gitignored).
- LLM provider must stay behind a single dispatch so switching is a config change, not a code change.

## Running locally
Backend: `cd backend && python3 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt && cp .env.example .env && uvicorn app.main:app --reload`
Frontend: `cd frontend && npm install && npm run dev`
Then open http://localhost:5173 . API docs at http://127.0.0.1:8000/docs .

## Owner notes
- Mahesh is comfortable with dev tools. He'll supply API keys in `.env` himself.
- Goal is both to **improve his English** and to **own/extend the project** — favor clean,
  extensible code over shortcuts.
