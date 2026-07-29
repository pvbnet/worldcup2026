#!/usr/bin/env bash
# Production-style server: built UI + API, no --reload. Uses $PORT (default 8080).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"
UVICORN="${ROOT}/.venv/bin/uvicorn"
if [[ ! -x "$UVICORN" ]]; then
  echo "Missing ${UVICORN}. Create the venv and install deps:" >&2
  echo "  cd dashboard/backend && python -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt" >&2
  exit 1
fi
cd "${ROOT}/app"
PORT="${PORT:-8080}"
echo ""
echo "Open http://127.0.0.1:${PORT}/  (http://localhost:${PORT}/)"
echo ""
exec "$UVICORN" main:app --host 0.0.0.0 --port "$PORT"
