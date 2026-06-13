#!/usr/bin/env bash
set -e

REPO="$(cd "$(dirname "$0")" && pwd)"
PIDS_FILE="$REPO/.pids"

if [[ -f "$PIDS_FILE" ]]; then
  echo "TalkBetter is already running. Run ./stop.sh first."
  exit 1
fi

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

echo ""
echo "  TalkBetter is running."
echo ""
echo "  App  →  http://localhost:5173"
echo "  API  →  http://127.0.0.1:8000/docs"
echo ""
echo "  Logs:  tail -f backend.log   or   tail -f frontend.log"
echo "  Stop:  ./stop.sh"
echo ""
