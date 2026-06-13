#!/usr/bin/env bash

REPO="$(cd "$(dirname "$0")" && pwd)"
PIDS_FILE="$REPO/.pids"

if [[ ! -f "$PIDS_FILE" ]]; then
  echo "TalkBetter is not running (no .pids file found)."
  exit 0
fi

read -r BACKEND_PID FRONTEND_PID < "$PIDS_FILE"

kill_pid() {
  local pid=$1 name=$2
  if kill -0 "$pid" 2>/dev/null; then
    kill "$pid" && echo "Stopped $name (PID $pid)"
  else
    echo "$name (PID $pid) was already stopped"
  fi
}

kill_pid "$BACKEND_PID"  "backend"
kill_pid "$FRONTEND_PID" "frontend"

rm -f "$PIDS_FILE"
echo "Done."
