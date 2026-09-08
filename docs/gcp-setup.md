# Google Cloud setup

GCP project and tooling setup for deploying the dashboard to **Cloud Run** with **Docker** and **Artifact Registry**. Uses the root [`Dockerfile`](../Dockerfile).

## Prerequisites

- Local Docker build and smoke test passing — see [docker-local.md](docker-local.md).
- A Google Cloud account with **billing** enabled on the project you use.
- [Google Cloud CLI (`gcloud`)](https://cloud.google.com/sdk/docs/install) installed.
- [Docker](https://docs.docker.com/engine/install/) installed if you will build images locally (optional if you use `gcloud builds submit`).

## 1. Project and login

```bash
gcloud auth login
gcloud auth application-default login   # optional; useful for local tools

export PROJECT_ID=world-cup-dashboard-v1
export REGION=us-central1              # pick a region near you

gcloud config set project "$PROJECT_ID"
```

Create a project if needed:

```bash
gcloud projects create "$PROJECT_ID" --name="World Cup 2026"
# Link billing in the Cloud Console: Billing → link project
```

## 2. Enable APIs

```bash
gcloud services enable \
  run.googleapis.com \
  artifactregistry.googleapis.com
```

For remote image builds without local Docker:

```bash
gcloud services enable cloudbuild.googleapis.com
```

## 3. Set up Artifact Registry (for Docker images)

```bash
export REPO=worldcup2026

gcloud artifacts repositories create "$REPO" \
  --repository-format=docker \
  --location="$REGION" \
  --description="World Cup 2026 dashboard images"
```

Authenticate Docker to push images:

```bash
gcloud auth configure-docker "${REGION}-docker.pkg.dev"
```

Image name pattern:

```bash
export IMAGE="${REGION}-docker.pkg.dev/${PROJECT_ID}/${REPO}/dashboard:latest"
```

## 4. Build and push the Docker image

Build and push image to Artifact Registry:

```bash
docker build -t "$IMAGE" .
docker push "$IMAGE"
```

If you already built locally as `worldcup2026-dashboard`:

```bash
docker tag worldcup2026-dashboard "$IMAGE"
docker push "$IMAGE"
```

Or build in GCP:

```bash
gcloud builds submit --tag "$IMAGE"
```

## 5. Deploy the Docker image to Cloud Run

Create or update the Cloud Run service:

```bash
gcloud run deploy worldcup2026-dashboard \
  --image "$IMAGE" \
  --region "$REGION" \
  --platform managed \
  --allow-unauthenticated \
  --port 8080 \
  --memory 2Gi \
  --cpu 2 \
  --timeout 3600 \
  --max-instances 1
```

The command prints the public HTTPS URL. Check `GET /api/health` on that host.

For the public web URL via Firebase Hosting (`worldcup-dashboard.web.app`), see [firebase-hosting.md](firebase-hosting.md).

## 6. Repeat deploys

After code or image changes:

```bash
docker build -t "$IMAGE" . && docker push "$IMAGE"
# or: gcloud builds submit --tag "$IMAGE"

gcloud run deploy worldcup2026-dashboard --image "$IMAGE" --region "$REGION"
```

**When to rebuild the image:** Any change that should appear in the running container — Python backend, model code, frontend source, `requirements.txt`, `package.json` / lockfile, committed files under `model/artifacts/`, or the [`Dockerfile`](../Dockerfile). The image bakes in the frontend build, Python deps, and a one-time fetch/ingest at build time.

**When a rebuild is not needed:**

- **Cloud Run settings only** (memory, CPU, timeout, `--max-instances`, env vars) — run `gcloud run deploy` with the existing `$IMAGE` and updated flags; no `docker build` or push.
- **New World Cup match data only** — locally, re-run `fetch_data.py --force --competitions world_cup` then ingest/train/simulate; on the running service, `POST /api/refresh-data` does the same without a new image.
- **Docs or local dev** — README, scripts used only on your machine, and `./start-dashboard-local.sh` do not affect the deployed container.

If you changed code but skip rebuild/push, Cloud Run keeps serving the previous image; redeploy alone does not pick up repo changes.

## Notes

- **Costs:** Cloud Run, Artifact Registry, and Cloud Build usage are billable; use [pricing calculators](https://cloud.google.com/products/calculator) and delete unused services/repos if you are experimenting.
- **Simulation jobs:** In-memory job state is per Cloud Run instance; `--max-instances 1` keeps polling reliable for background sim jobs on a small public demo.
- **Refresh data:** `POST /api/refresh-data` can run for a long time; keep request timeout at or below Cloud Run’s maximum (3600s).
