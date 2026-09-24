#!/usr/bin/env bash
set -e

REPO="$(cd "$(dirname "$0")" && pwd)"

echo "Restarting TalkBetter..."
"$REPO/stop.sh" || true
"$REPO/start.sh"
