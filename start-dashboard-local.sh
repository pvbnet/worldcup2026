#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
export PATH="${HOME}/.local/node-v20.18.0-linux-x64/bin:${PATH}"

echo "Starting backend at http://localhost:8000 ..."
(cd "$ROOT/dashboard/backend/app" && ../.venv/bin/uvicorn main:app --reload --host 0.0.0.0 --port 8000) &
BACKEND_PID=$!

sleep 2
if ! curl -sf http://localhost:8000/api/health >/dev/null; then
  echo "Backend failed to start. Check dashboard/backend/.venv and requirements.txt"
  kill "$BACKEND_PID" 2>/dev/null || true
  exit 1
fi

echo "Starting frontend on http://localhost:5173 ..."
(cd "$ROOT/dashboard/frontend" && npm run dev) &
FRONTEND_PID=$!

sleep 2
echo ""
echo "Dashboard: http://localhost:5173/"
echo "Press Ctrl+C to stop both servers."

trap 'kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; exit' INT TERM
wait
