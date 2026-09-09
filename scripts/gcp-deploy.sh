#!/usr/bin/env bash
# Rebuild the Docker image, push to Artifact Registry, deploy to Cloud Run.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

PROJECT_ID="${PROJECT_ID:-world-cup-dashboard-v1}"
REGION="${REGION:-us-central1}"
REPO="${REPO:-worldcup2026}"
SERVICE="${SERVICE:-worldcup2026-dashboard}"
IMAGE="${IMAGE:-${REGION}-docker.pkg.dev/${PROJECT_ID}/${REPO}/dashboard:latest}"

if ! command -v docker >/dev/null 2>&1; then
  echo "Docker not found. Install: https://docs.docker.com/engine/install/" >&2
  exit 1
fi
if ! command -v gcloud >/dev/null 2>&1; then
  echo "gcloud not found. Install: https://cloud.google.com/sdk/docs/install" >&2
  exit 1
fi

echo "Building ${IMAGE} ..."
docker build -t "$IMAGE" .

echo "Pushing ${IMAGE} ..."
docker push "$IMAGE"

echo "Deploying ${SERVICE} ..."
gcloud run deploy "$SERVICE" \
  --project "$PROJECT_ID" \
  --image "$IMAGE" \
  --region "$REGION" \
  --platform managed \
  --allow-unauthenticated \
  --port 8080 \
  --memory 2Gi \
  --cpu 2 \
  --timeout 3600 \
  --max-instances 1
