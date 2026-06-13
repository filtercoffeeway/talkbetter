# TalkBetter

A local app to improve spoken English — fewer filler words, better pace, correct
grammar, clearer communication, and a more American accent.

Record yourself in the browser; a Python backend transcribes and analyzes the audio
and returns feedback. Runs entirely on your machine (Phases 2–3 make optional cloud calls).

## Full spec
Open **`docs/spec.html`** in a browser — it's the detailed, phase-by-phase build plan.
For AI/coding-session context, see **`CLAUDE.md`**.

## Status
Scaffolded, not yet implemented. Build in phase order (service modules are stubs).

## Quick start

Prerequisites: `python@3.11`, `node`, `ffmpeg`.

```bash
# Backend
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env          # Phase 1 needs no API keys
uvicorn app.main:app --reload # http://127.0.0.1:8000  (docs: /docs)

# Frontend (separate terminal)
cd frontend
npm install
npm run dev                   # http://localhost:5173
```

## Phases
1. Transcription + pace + filler words — local, no keys.
2. Grammar + clarity — needs an LLM key (Claude by default).
3. American accent — needs an Azure key.
4. Progress tracking & polish — optional.
