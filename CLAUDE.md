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
- **Accent:** local wav2vec2 phoneme model + `espeak-ng` by default (`PRONUNCIATION_PROVIDER=local`, no key);
  **Azure Pronunciation Assessment** swappable (`PRONUNCIATION_PROVIDER=azure`) — Phase 3.
- **ffmpeg** must be on the host for audio transcode; **espeak-ng** for local accent scoring.

## Build phases (do in order; each has acceptance criteria in spec.html)
1. **Phase 1 — Transcription + pace + fillers.** Local, no API keys. First working loop.
2. **Phase 2 — Grammar + clarity.** Needs an LLM key.
3. **Phase 3 — American accent.** Reference-based (user reads a sentence). Local by default; Azure optional.
4. **Phase 4 — Progress tracking & polish.** Optional; SQLite history + charts.

## Where things live
- API contract / response shapes: `backend/app/models/schemas.py` (single source of truth).
- Endpoint orchestration: `backend/app/routers/analysis.py` (`POST /api/analyze`).
- Services: `backend/app/services/{transcription,filler_pace,llm_feedback,pronunciation}.py`
  (`pronunciation.py` dispatches to `pronunciation_local.py` / `pronunciation_azure.py`).
- Config (reads `.env`): `backend/app/config.py`; template in `backend/.env.example`.
- `SAVE_RECORDINGS=true` archives accent-practice audio + its sentence to `data/recordings/`
  (`services/recordings.py`); `python -m scripts.compare_providers` (from `backend/`) re-scores them
  with both the local and Azure providers side by side.
- Frontend entry: `frontend/src/App.jsx` (has both "free speaking" and "accent practice" modes).
- **Phase 4 (built): profiles + progress.** SQLite layer `backend/app/db.py` (stdlib `sqlite3`, DB at
  `data/talkbetter.db`, gitignored); persistence/queries `backend/app/services/storage.py`; endpoints
  `backend/app/routers/{profiles,history}.py` (`GET/POST /api/profiles`, `GET /api/history`).
  Frontend: `ProfilePicker.jsx` (name-only, no auth) + `Dashboard.jsx` (Chart.js trends + streak).
  `/api/analyze` takes an optional `profile_id` form field; when present the session is saved and the
  response includes `session_id`. Persistence works even before Phases 1–3 land (metrics nullable).
- **30-day program (built, the default view).** 30 days × 30 min. Content in
  `backend/app/services/program_content.py`; scoring + assembly in `services/program.py`; endpoints
  `GET /api/program[?profile_id=]` and `GET /api/program/benchmarks?profile_id=` (`routers/program.py`).
  Every day opens with a **fixed benchmark** (same read-aloud passage + a 90 s opinion answer with a
  rotating topic in a fixed format). Only the first take per day is stored (`benchmark_results`,
  UNIQUE per day+part), so the weekly trend is honest. Practice results live in
  `program_activity_results` keyed `(profile_id, day, activity_id)`. `/api/analyze` takes
  `program_day` + `activity_id`; speak activities also get `llm_feedback.assess_speaking` (confidence /
  structure / vocabulary rubric, schema-enforced output via `messages.parse`). **Don't change the benchmark passage, prompt format,
  rubric anchors or scoring weights mid-program** — that moves the denominator. Frontend: `Program.jsx`.

## Conventions
- Keep `schemas.py` and the API section of `docs/spec.html` in sync — the frontend trusts those field names.
- Later-phase fields (`language`, `accent`) are nullable; the frontend renders only present sections,
  so a partially-built backend still works end to end.
- Don't commit `.env` or anything under `data/recordings/` (already gitignored).
- LLM and pronunciation providers must each stay behind a single dispatch (`llm_feedback.analyze`,
  `pronunciation.assess`) so switching is a config change, not a code change.

## Running locally
Backend: `cd backend && python3 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt && cp .env.example .env && uvicorn app.main:app --reload`
Frontend: `cd frontend && npm install && npm run dev`
Then open http://localhost:5173 . API docs at http://127.0.0.1:8000/docs .

## Owner notes
- Mahesh is comfortable with dev tools. He'll supply API keys in `.env` himself.
- Goal is both to **improve his English** and to **own/extend the project** — favor clean,
  extensible code over shortcuts.
