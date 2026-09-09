# Firebase Hosting

Public URL in front of the existing **Cloud Run** deployment. Firebase Hosting rewrites all requests to the Cloud Run service; the container is unchanged.

**Public URLs:** https://worldcup-dashboard.web.app and https://worldcup-dashboard.firebaseapp.com

## Architecture

```text
Browser → Firebase Hosting (worldcup-dashboard.web.app)
        → rewrite ** → Cloud Run (worldcup2026-dashboard, us-central1)
        → same SPA + /api as direct *.run.app
```

Config: [`firebase.json`](../firebase.json) (site + rewrite), [`.firebaserc`](../.firebaserc) (Firebase/GCP project).

## Prerequisites

- Cloud Run service deployed — see [gcp-setup.md](gcp-setup.md).
- Firebase project linked to the same GCP project (`world-cup-dashboard-v1`).
- Firebase Hosting site `worldcup-dashboard` created in the Firebase console.
- [Firebase CLI](https://firebase.google.com/docs/cli): `npm install -g firebase-tools` or `npx firebase-tools`.

## One-time setup

```bash
firebase login
firebase use world-cup-dashboard-v1
```

Confirm the Cloud Run service name:

```bash
gcloud run services describe worldcup2026-dashboard \
  --region=us-central1 \
  --format='value(metadata.name)'
```

If `firebase deploy` or the live site returns **403**, grant the Firebase Hosting service agent invoker on Cloud Run:

```bash
PROJECT_ID=world-cup-dashboard-v1
PROJECT_NUMBER=$(gcloud projects describe "$PROJECT_ID" --format='value(projectNumber)')
gcloud run services add-iam-policy-binding worldcup2026-dashboard \
  --region=us-central1 \
  --member="serviceAccount:service-${PROJECT_NUMBER}@gcp-sa-firebasehosting.iam.gserviceaccount.com" \
  --role="roles/run.invoker"
```

Often unnecessary when Cloud Run is already `--allow-unauthenticated`.

## Deploy Hosting

From the repo root:

```bash
chmod +x scripts/firebase-deploy.sh   # once
./scripts/firebase-deploy.sh
```

Or:

```bash
firebase deploy --only hosting
```

This updates Hosting rewrites/CDN only — it does **not** build or push the Docker image.

Smoke test:

```bash
curl https://worldcup-dashboard.web.app/api/health
```

Open https://worldcup-dashboard.web.app/ in a browser.

## When to redeploy Firebase vs Cloud Run

| Change | Action |
|--------|--------|
| App code, Docker image, deps | `./scripts/gcp-deploy.sh` |
| Firebase `.json` / rewrite only | `./scripts/firebase-deploy.sh` |
| Cloud Run settings only (memory, CPU, timeout) | `gcloud run deploy` with same image |

## See also

- [gcp-setup.md](gcp-setup.md) — Artifact Registry and Cloud Run
- [docker-local.md](docker-local.md) — local container build
- [architecture.md](architecture.md) — runtime modes and data flow
