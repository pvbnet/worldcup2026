#!/usr/bin/env bash
set -euo pipefail
export PATH="${HOME}/.local/node-v20.18.0-linux-x64/bin:${PATH}"
cd "$(dirname "$0")"
exec npm run dev
