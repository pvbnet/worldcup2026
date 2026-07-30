#!/usr/bin/env bash
# Local Docker demo: build image, run container, smoke-test
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
IMAGE="${IMAGE:-worldcup2026-dashboard}"
PORT="${PORT:-8080}"

if ! command -v docker >/dev/null 2>&1; then
  echo "Docker not found. Install: https://docs.docker.com/engine/install/" >&2
  exit 1
fi

echo "Building ${IMAGE} ..."
docker build -t "$IMAGE" .

echo ""
echo "Starting container on http://localhost:${PORT}/ (Ctrl+C to stop) ..."
echo "In another terminal:"
echo "  curl http://localhost:${PORT}/api/health"
echo "  curl -s -o /dev/null -w '%{http_code}\\n' http://localhost:${PORT}/teams"
echo ""
docker run --rm -p "${PORT}:${PORT}" -e "PORT=${PORT}" "$IMAGE"
