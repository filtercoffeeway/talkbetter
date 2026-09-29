#!/usr/bin/env bash
set -e

REPO="$(cd "$(dirname "$0")" && pwd)"
PIDS_FILE="$REPO/.pids"

if [[ -f "$PIDS_FILE" ]]; then
  echo "TalkBetter is already running. Run ./stop.sh first."
  exit 1
fi

# ---- Prerequisites ----
# Hard requirements stop here; optional ones only warn (the app still runs,
# accent scoring is skipped).
install_hint() {
  if [[ "$(uname)" == "Darwin" ]]; then echo "brew install $1"; else echo "sudo apt install $1"; fi
}
missing=0
if ! command -v python3 >/dev/null 2>&1 || \
   ! python3 -c 'import sys; sys.exit(sys.version_info < (3, 11))'; then
  echo "✗ Python 3.11+ is required (found: $(python3 --version 2>&1 || echo none))."
  missing=1
fi
if ! command -v npm >/dev/null 2>&1; then
  echo "✗ Node.js (npm) is required — install from https://nodejs.org or: $(install_hint node)"
  missing=1
fi
[[ $missing -eq 1 ]] && exit 1
for tool in ffmpeg espeak-ng; do
  if ! command -v "$tool" >/dev/null 2>&1; then
    echo "⚠ $tool not found — accent scoring will be skipped. Install with: $(install_hint $tool)"
  fi
done

# ---- Backend ----
cd "$REPO/backend"

if [[ ! -d .venv ]]; then
  echo "Creating Python venv..."
  python3 -m venv .venv
fi

source .venv/bin/activate

if [[ ! -f .env ]]; then
  cp .env.example .env
  echo "Created backend/.env from .env.example — add your API keys there."
fi

echo "Installing Python packages (first run downloads ~2 GB, mostly PyTorch)..."
pip install -q -r requirements.txt

uvicorn app.main:app --reload --host 127.0.0.1 --port 8000 \
  > "$REPO/backend.log" 2>&1 &
BACKEND_PID=$!

# ---- Frontend ----
cd "$REPO/frontend"

if [[ ! -d node_modules ]]; then
  echo "Installing frontend dependencies..."
  npm install -q
fi

npm run dev > "$REPO/frontend.log" 2>&1 &
FRONTEND_PID=$!

# ---- Save PIDs ----
echo "$BACKEND_PID $FRONTEND_PID" > "$PIDS_FILE"

# ---- Wait for servers to be ready ----
echo "Starting servers..."
for i in $(seq 1 20); do
  sleep 0.5
  if curl -s http://127.0.0.1:8000/api/health > /dev/null 2>&1 && \
     curl -s http://localhost:5173 > /dev/null 2>&1; then
    break
  fi
done

if ! curl -s http://127.0.0.1:8000/api/health > /dev/null 2>&1; then
  echo ""
  echo "  ⚠ The backend didn't answer yet. It may still be starting — or check: tail backend.log"
fi

echo ""
echo "  TalkBetter is running."
echo ""
echo "  App  →  http://localhost:5173"
echo "  API  →  http://127.0.0.1:8000/docs"
echo ""
echo "  Logs:  tail -f backend.log   or   tail -f frontend.log"
echo "  Stop:  ./stop.sh"
echo ""
