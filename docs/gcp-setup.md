# Google Cloud setup (minimal)

GCP project and tooling setup for deploying the dashboard to **Cloud Run** with **Docker** and **Artifact Registry**. Uses the root [`Dockerfile`](../Dockerfile) (same image as local Docker).

## Prerequisites

- Local Docker build and smoke test passing — see [docker-local.md](docker-local.md).
- A Google Cloud account with **billing** enabled on the project you use.
- [Google Cloud CLI (`gcloud`)](https://cloud.google.com/sdk/docs/install) installed.
- [Docker](https://docs.docker.com/engine/install/) installed if you will build images locally (optional if you use `gcloud builds submit`).

## 1. Project and login

```bash
gcloud auth login
gcloud auth application-default login   # optional; useful for local tools

export PROJECT_ID=your-gcp-project-id
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

## 3. Artifact Registry (Docker images)

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

## 4. Deploy

Build and push (local Docker):

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

## 5. Repeat deploys

After code or image changes:

```bash
docker build -t "$IMAGE" . && docker push "$IMAGE"
# or: gcloud builds submit --tag "$IMAGE"

gcloud run deploy worldcup2026-dashboard --image "$IMAGE" --region "$REGION"
```

## Notes

- **Costs:** Cloud Run, Artifact Registry, and Cloud Build usage are billable; use [pricing calculators](https://cloud.google.com/products/calculator) and delete unused services/repos if you are experimenting.
- **Simulation jobs:** In-memory job state is per Cloud Run instance; `--max-instances 1` keeps polling reliable for background sim jobs on a small public demo.
- **Refresh data:** `POST /api/refresh-data` can run for a long time; keep request timeout at or below Cloud Run’s maximum (3600s).
