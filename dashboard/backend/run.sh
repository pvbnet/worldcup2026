#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/app"
exec ../.venv/bin/uvicorn main:app --reload --host 0.0.0.0 --port 8000
