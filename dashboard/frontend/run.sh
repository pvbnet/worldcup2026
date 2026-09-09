#!/usr/bin/env bash
# Development: Serve frontend at http://localhost:5173
set -euo pipefail
# shellcheck source=../env.sh
source "$(cd "$(dirname "$0")/.." && pwd)/env.sh"
cd "$(dirname "$0")"
exec npm run dev
