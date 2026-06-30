# TalkBetter 🎙️

A local app to improve spoken English — fewer filler words, better pace, correct grammar, clearer communication, and a more American accent.

Record yourself in the browser; the Python backend transcribes and analyzes your audio and returns detailed feedback. Runs entirely on your machine (Phases 2–3 make optional cloud calls).

## Features

**Phase 1 — Local, no API keys required**
- 🎤 Browser-based audio recording
- 📝 Local speech transcription (faster-whisper)
- 🔢 Words per minute + speaking pace analysis
- ⏸️ Long pause detection (>1.5s gaps)
- 🚫 Filler word detection — tracks "um", "uh", "like", "basically", "you know", "sort of" and more, with per-word counts and rate per minute

**Phase 2 — Grammar & clarity (Claude API)**
- ✍️ Grammar and sentence structure feedback
- 💡 Clarity and communication improvement suggestions

**Phase 3 — Accent coaching (Azure Speech API)**
- 🗣️ American accent pronunciation analysis

**Phase 4 — Progress tracking**
- 📊 Session history and improvement trends
- 👤 User profiles

## Quick Start

**Prerequisites:** Python 3.11+, Node.js, ffmpeg

```bash
# Backend
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env        # Phase 1 needs no API keys
uvicorn app.main:app --reload  # http://127.0.0.1:8000

# Frontend (separate terminal)
cd frontend
npm install
npm run dev                  # http://localhost:5173
```

API docs available at `http://127.0.0.1:8000/docs`

## Tech Stack

- **Frontend:** React + Vite — browser-based audio recording
- **Backend:** FastAPI + Uvicorn (Python)
- **Transcription:** faster-whisper — runs fully locally
- **Filler & Pace Analysis:** Custom NLP pipeline (no external API)
- **Grammar Feedback:** Claude (Anthropic API) — Phase 2
- **Accent Analysis:** Azure Speech API — Phase 3
- **Storage:** SQLite for session history and profiles

## API Overview

| Endpoint | Description |
|----------|-------------|
| `POST /analysis/` | Submit audio, get full feedback report |
| `GET /history/` | Retrieve past sessions |
| `GET/POST /profiles/` | Manage user profiles |

## Configuration

All settings via `backend/.env`:

```
ANTHROPIC_API_KEY=...   # Phase 2: grammar feedback
AZURE_SPEECH_KEY=...    # Phase 3: accent analysis
```

Phase 1 (transcription + filler + pace) works with no keys.
