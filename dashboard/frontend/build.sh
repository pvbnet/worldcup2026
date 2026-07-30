#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
# shellcheck source=../../scripts/env.sh
source "$ROOT/scripts/env.sh"
cd "$(dirname "$0")"
exec npm run build
