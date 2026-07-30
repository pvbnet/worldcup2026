#!/usr/bin/env bash
# Development: Serve frontend at http://localhost:5173
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
# shellcheck source=../../scripts/env.sh
source "$ROOT/scripts/env.sh"
cd "$(dirname "$0")"
exec npm run dev
