#!/usr/bin/env bash
# Deploy Firebase Hosting config (rewrites to Cloud Run). Does not rebuild the container.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

if ! command -v firebase >/dev/null 2>&1; then
  echo "Firebase CLI not found. Install: npm install -g firebase-tools" >&2
  exit 1
fi

firebase deploy --only hosting
