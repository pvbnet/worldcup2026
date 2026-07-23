#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
export PATH="${HOME}/.local/node-v20.18.0-linux-x64/bin:${PATH}"

echo "Starting backend on http://0.0.0.0:8000 ..."
(cd "$ROOT/dashboard/backend/app" && ../.venv/bin/uvicorn main:app --reload --host 0.0.0.0 --port 8000) &
BACKEND_PID=$!

sleep 2
if ! curl -sf http://127.0.0.1:8000/api/health >/dev/null; then
  echo "Backend failed to start. Check dashboard/backend/.venv and requirements.txt"
  kill "$BACKEND_PID" 2>/dev/null || true
  exit 1
fi

echo "Starting frontend on http://localhost:5173 ..."
(cd "$ROOT/dashboard/frontend" && npm run dev) &
FRONTEND_PID=$!

sleep 2
WSL_IP="$(hostname -I | awk '{print $1}')"
echo ""
echo "Dashboard ready:"
echo "  WSL (always works from Windows Chrome): http://${WSL_IP}:5173"
echo "  localhost (when WSL port forwarding works): http://localhost:5173"
echo ""
echo "If localhost fails in Chrome but the WSL IP works, run in Windows PowerShell:"
echo "  wsl --shutdown"
echo "Then reopen WSL and start this script again."
echo ""
echo "Press Ctrl+C to stop both servers."

trap 'kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; exit' INT TERM
wait
