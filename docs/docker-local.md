# Local Docker build on WSL

Build and run the dashboard container before pushing to GCP.

## Prerequisites

- Docker installed and engine running.
- Add your user to the `docker` group (optional but recommended):

```bash
sudo usermod -aG docker $USER && newgrp docker
```

## Start the Docker Engine if not already running

```bash
sudo service docker start
```

## Build and run

```bash
./scripts/docker-local-test.sh
```

Or:

```bash
docker build -t worldcup2026-dashboard .
docker run --rm -p 8080:8080 -e PORT=8080 worldcup2026-dashboard
```

Smoke test (another terminal):

```bash
curl http://localhost:8080/api/health
```

Open **http://localhost:8080/**.

The [`Dockerfile`](../Dockerfile) pulls base images from **AWS ECR Public** (`public.ecr.aws/docker/library/...`).

## WSL issue: `lookup ... on 10.255.255.254:53: no such host`

`docker pull` / `docker build` use the **host** `/etc/resolv.conf`, not the `"dns"` entry in `/etc/docker/daemon.json` (that setting is for containers only).

WSL often sets `nameserver 10.255.255.254`, which breaks Docker pulls even when `curl` works.

**Fix (one-time in WSL):**

```bash
sudo tee /etc/wsl.conf >/dev/null <<'EOF'
[network]
generateResolvConf = false
EOF

sudo rm -f /etc/resolv.conf
sudo tee /etc/resolv.conf >/dev/null <<'EOF'
nameserver 8.8.8.8
nameserver 8.8.4.4
EOF
```

**Restart WSL from Windows PowerShell** (required so WSL picks this up):

```powershell
wsl --shutdown
```

Reopen WSL in terminal, then:

```bash
cat /etc/resolv.conf          # should show 8.8.8.8, not 10.255.255.254
sudo service docker start
docker pull public.ecr.aws/docker/library/node:20-bookworm-slim
cd ~/work/repos/worldcup2026
docker build -t worldcup2026-dashboard .
```
