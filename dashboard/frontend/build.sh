#!/usr/bin/env bash
set -euo pipefail
# shellcheck source=../env.sh
source "$(cd "$(dirname "$0")/.." && pwd)/env.sh"
cd "$(dirname "$0")"
exec npm run build
