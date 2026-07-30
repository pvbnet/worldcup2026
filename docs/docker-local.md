# Local Docker build

Build and run the dashboard container before pushing to GCP.

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
sudo docker pull public.ecr.aws/docker/library/node:20-bookworm-slim
cd ~/work/repos/worldcup2026
sudo docker build -t worldcup2026-dashboard .
```

Keep `"ipv6": false` in `/etc/docker/daemon.json` if you added it earlier.

## WSL issue: `network is unreachable` on IPv6

If pulls fail with an IPv6 address (`dial tcp [2606:...]:443`):

```bash
printf '%s\n' \
  'net.ipv6.conf.all.disable_ipv6 = 1' \
  'net.ipv6.conf.default.disable_ipv6 = 1' \
  | sudo tee /etc/sysctl.d/99-disable-ipv6.conf
sudo sysctl -p /etc/sysctl.d/99-disable-ipv6.conf
sudo service docker restart
```

**Check:** `curl -4 -s -o /dev/null -w "%{http_code}\n" https://public.ecr.aws/` → 308 is OK.
