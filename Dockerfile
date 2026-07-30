# Stage 1: build React frontend
# Use AWS ECR Public (Docker Hub mirror) — avoids auth.docker.io IPv6 issues on some WSL setups.
FROM public.ecr.aws/docker/library/node:20-bookworm-slim AS frontend
WORKDIR /src
COPY dashboard/frontend/package.json dashboard/frontend/package-lock.json dashboard/frontend/
RUN cd dashboard/frontend && npm ci
COPY dashboard/frontend/ dashboard/frontend/
RUN cd dashboard/frontend && npm run build

# Stage 2: Python runtime
FROM public.ecr.aws/docker/library/python:3.12-slim-bookworm AS runtime
WORKDIR /app

COPY model/requirements.txt model/requirements.txt
COPY dashboard/backend/requirements.txt dashboard/backend/requirements.txt
RUN pip install --no-cache-dir \
    -r model/requirements.txt \
    -r dashboard/backend/requirements.txt

COPY model/ model/
COPY dashboard/backend/ dashboard/backend/
COPY --from=frontend /src/dashboard/artifacts/build dashboard/artifacts/build/

RUN cd model && python scripts/fetch_data.py && python scripts/ingest.py

ENV PORT=8080
WORKDIR /app/dashboard/backend/app
EXPOSE 8080
CMD ["sh", "-c", "exec uvicorn main:app --host 0.0.0.0 --port ${PORT}"]
