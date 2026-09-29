# TalkBetter 🎙️

**A private, local speaking coach for non-native English speakers.**
Record yourself in the browser and get feedback on filler words, pace, grammar,
clarity, confidence, how well you structure your thoughts, and your American accent,
and follow a **30-day, 30-minutes-a-day program** that measures your progress honestly.

Speech recognition and accent scoring run on your own machine. Nothing is uploaded
unless you add an API key (see [Privacy](#privacy)).

---

## What you get

### 📅 30 Days to Confident English
A structured 30-day course, 30 minutes a day:

| Part | Time | What you do |
|---|---|---|
| **Daily benchmark** | 5 min | Read the **same passage** aloud and answer a **90-second question** (the topic changes daily, the format never does). Only your first take counts, so the score is an honest measure you can compare week to week. |
| **Pronunciation** | 8 min | Two sentences that drill the day's sounds, with a 🔊 button to hear them in American English first. |
| **Speaking practice** | 17 min | Two open-ended answers practising one technique: silent pauses instead of "um", answering first, PREP, STAR stories, small talk, disagreeing politely, and interview answers. |

The weeks build on each other: **sounds & filler awareness → rhythm & structured
thinking → real conversations → confidence under pressure**. Review days (7, 14, 21, 28)
repeat earlier prompts so you can hear the difference. A trend chart and a
week-by-week table show whether your benchmark is going up.

### 🎤 Practice
Free speaking with instant feedback, or read any sentence you like for accent scoring.

### 📈 Progress
Your history across all sessions: pace, fillers, clarity and pronunciation over time, plus a practice streak.

### What each recording is scored on

| Feedback | How | Needs |
|---|---|---|
| Transcript, words per minute, long pauses | [faster-whisper](https://github.com/SYSTRAN/faster-whisper), locally | nothing |
| Filler words ("um", "like", "you know", …) | local counting on the transcript | nothing |
| American accent (per word and per sound) | a local phoneme model (wav2vec2) compared with American pronunciations from espeak-ng | `espeak-ng`, `ffmpeg` |
| Grammar you can hear, clarity | Claude | Anthropic API key |
| Confidence, structure (thought process), vocabulary, and a "say it like this" rewrite | Claude, scored against a fixed rubric | Anthropic API key |

Without a key the app still works: you get the transcript, pace, fillers and accent scoring.

---

## Quick start (macOS / Linux)

### 1. Install the prerequisites

| | macOS ([Homebrew](https://brew.sh)) | Ubuntu / Debian |
|---|---|---|
| Python 3.11+, Node.js 18+, ffmpeg, espeak-ng | `brew install python node ffmpeg espeak-ng` | `sudo apt install python3 python3-venv nodejs npm ffmpeg espeak-ng` |

> **Ubuntu 22.04 or older:** the `nodejs` package is too old for the frontend. Install Node 18+ from [nodejs.org](https://nodejs.org) or [NodeSource](https://github.com/nodesource/distributions) instead.
>
> **Windows:** use [WSL2](https://learn.microsoft.com/windows/wsl/install) with Ubuntu and follow the Linux steps. This hasn't been tested.

### 2. Get the code and start it

```bash
git clone https://github.com/filtercoffeeway/talkbetter.git
cd talkbetter
./start.sh
```

`start.sh` checks the prerequisites, creates a Python virtual environment, installs
everything, creates `backend/.env`, and starts both servers.

Then open **http://localhost:5173**, create a profile with your name, and allow microphone access.

### 3. (Recommended) Add an Anthropic API key

Grammar, clarity, confidence and structure scoring need a key from
[console.anthropic.com](https://console.anthropic.com). Put it in `backend/.env`:

```bash
ANTHROPIC_API_KEY=sk-ant-...
```

Then restart with `./restart.sh`.

A typical day of the program makes a handful of short requests. It costs well under a
dollar a day with the default model (Claude Sonnet), and less with `claude-haiku-4-5`.

### Stop / restart

```bash
./stop.sh
./restart.sh
```

Logs go to `backend.log` and `frontend.log` in the repo root.

---

## ⏳ The first run is slow (once)

| What | Size | When |
|---|---|---|
| Python packages (mostly PyTorch) | ~2 GB | during `./start.sh` |
| Whisper speech model (`small` by default) | ~500 MB | your first recording |
| Accent model | ~1.2 GB | your first read-aloud |

After that everything is cached and starts quickly. Expect roughly 5–20 seconds of
analysis per recording on a laptop, and longer with bigger Whisper models.

---

## Configuration

All settings live in `backend/.env`. See [`backend/.env.example`](backend/.env.example) for the full list with comments.

| Setting | Default | What it does |
|---|---|---|
| `ANTHROPIC_API_KEY` | *(empty)* | Turns on grammar, clarity, confidence and structure feedback. |
| `ANTHROPIC_MODEL` | `claude-sonnet-5-5` | `claude-haiku-4-5` is cheaper and faster; Sonnet judges more reliably. |
| `WHISPER_MODEL` | `small` | `base` is faster; `large-v3` is the most accurate but slow on CPU. |
| `PRONUNCIATION_PROVIDER` | `local` | `local` judges how *American* you sound. `azure` (needs `AZURE_SPEECH_KEY`/`REGION`) judges how *understandable* you are and is much more lenient about accent. |
| `SAVE_RECORDINGS` | `false` | Keep read-aloud audio in `data/recordings/` for replaying or re-scoring. |

> 💡 **Doing the 30-day program?** Choose your models before Day 1 and keep them. Changing a model changes how scores are calculated, which makes your trend harder to compare.

---

## Privacy

- **Audio never leaves your machine** with the default settings. Transcription and accent scoring are local.
- With an Anthropic key, the **transcript text** (not audio) is sent to the Claude API for feedback.
- With `PRONUNCIATION_PROVIDER=azure`, read-aloud **audio** is sent to Azure.
- Your history is stored locally in `data/talkbetter.db` (SQLite). It is gitignored, as are `backend/.env` and `data/recordings/`.

---

## Troubleshooting

| Problem | Fix |
|---|---|
| No microphone prompt, or recording fails | Use Chrome or Edge on `http://localhost:5173`, and check the browser's site permissions for the microphone. |
| No "American accent" section | Install `espeak-ng` and `ffmpeg`, then `./restart.sh`. The backend's startup lines in `backend.log` show whether each part is ON. |
| No grammar or confidence feedback | Add `ANTHROPIC_API_KEY` to `backend/.env` and restart. |
| "TalkBetter is already running" | `./stop.sh`, then `./start.sh`. |
| Port 8000 or 5173 already in use | Find what's using it with `lsof -i :8000` (or `:5173`) and stop it. |
| The first analysis takes minutes | Models are downloading; this only happens once (see above). |

**Start the 30-day program over** (keeps your profile, erases its results):

```bash
cd backend
.venv/bin/python -m scripts.reset_profile "Your Name"                  # everything
.venv/bin/python -m scripts.reset_profile "Your Name" --program-only   # just the 30-day program
```

---

## Manual setup (without start.sh)

```bash
# Backend (terminal 1)
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload          # http://127.0.0.1:8000  (API docs at /docs)

# Frontend (terminal 2)
cd frontend
npm install
npm run dev                            # http://localhost:5173
```

---

## Development

```bash
cd backend && .venv/bin/python -m pytest      # fast; no network or API keys needed
cd frontend && npm run build
```

| Where | What |
|---|---|
| `backend/app/models/schemas.py` | API contract, the single source of truth for response shapes |
| `backend/app/routers/` | `analysis` (`POST /api/analyze`), `program`, `history`, `profiles` |
| `backend/app/services/program_content.py` | The 30-day curriculum: edit text freely, but keep day numbers and activity ids |
| `backend/app/services/program.py` | Program scoring and progress |
| `backend/app/services/` | transcription, fillers/pace, LLM feedback, pronunciation (`local` / `azure`) |
| `frontend/src/` | React + Vite UI (`components/Program.jsx` is the 30-day view) |
| `docs/spec.html` | Detailed design spec and API reference |

**Tech stack:** React + Vite · FastAPI · faster-whisper · wav2vec2 + espeak-ng · Claude API · SQLite · Chart.js

---

## License

[MIT](LICENSE)
