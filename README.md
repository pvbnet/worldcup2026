# World Cup 2026 Predictive Dashboard

Interactive dashboard ranking national soccer teams and estimating 2026 World Cup win probabilities using World Cup finals (2018, 2022, 2026) plus continental tournaments (Euro, Copa América, AFCON) and World Cup qualifiers for denser team-strength history. The 2010 and 2014 World Cups are intentionally excluded from training.

## Project layout

```
worldcup/
  model/          # data ingest, Elo training, evaluation, simulation
  dashboard/      # FastAPI backend + React frontend
```

## Outcome model

| Piece | Purpose |
|---|---|
| **Elo ratings** | Team strength updated after each match (training engine) |
| **FIFA rankings** | Converted to pseudo-Elo for an alternate strength source |
| **Elo / FIFA toggle** | Binary switch: Monte Carlo match outcomes use either trained Elo or FIFA-based ratings |
| **Monte Carlo sim** | Re-simulates the full 2026 tournament from the group stage → stage-reach and win probabilities |

There is a single match-outcome engine (Elo win probabilities). Strength input is either trained Elo or FIFA pseudo-Elo.

### How the tournament is simulated

Each Monte Carlo trial re-simulates **from the group stage** (always sampling match outcomes from the model — not locking in played results):

1. **Groups** — 12 groups of 4; top **2** from each group advance (24 teams).
2. **No real Round of 32** — the FIFA 2026 format (32 knockout teams via best third-place teams) is **not** modeled. In the UI, **P(R32)** means the probability of finishing top-2 in the group (advancing into the sim’s knockout path).
3. **Round of 16** — those 24 advancers are ranked by the active strength ratings (Elo or FIFA pseudo-Elo); the **top 16** enter an Elo-seeded bracket. The other 8 group advancers are eliminated without playing knockout matches.
4. **Knockout** — R16 → QF → SF → Final is played by pairing adjacent seeds; draws are resolved with an Elo tie-break.

From many trials the dashboard reports **P(R32), P(R16), P(QF), P(SF), P(Final), P(Win WC)** (monotonic by construction).

## Dashboard UI

Top nav (default first):

- **Groups & teams** — group standings (played matches) and team detail
- **Knockout Stage** — actual 2026 knockout fixtures and results (R32→Final, including third place), left/right bracket layout
- **Predictions** — Elo/FIFA toggle; Monte Carlo run count (1000–5000); rankings table with stage-reach probabilities and an inline win-probability bar; progress overlay while sims run

## Setup

Uses **pyenv** (Python 3.12.3) with local virtualenvs in each component.

### 1. Model pipeline

```bash
cd /home/pvb/work/proj/worldcup/model
pyenv local 3.12.3
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

python scripts/fetch_data.py   # download World Cup + Euro/Copa/AFCON/qualifiers
python scripts/ingest.py
python scripts/train.py
python scripts/simulate.py     # writes worldcup_elo.json and worldcup_fifa.json
```

`fetch_data.py` accepts `--competitions` (subset) and `--force` (re-download). `ingest.py` still auto-fetches missing raw files as a fallback.

Artifacts are written to:
- `model/data/` — raw and processed match data
- `model/artifacts/training/` — Elo ratings
- `model/artifacts/evaluation/` — backtest metrics (Elo vs FIFA on WC 2022)
- `model/artifacts/predictions/` — stage-reach and win probabilities per strength

### 2. Dashboard backend

```bash
cd /home/pvb/work/proj/worldcup/dashboard/backend
pyenv local 3.12.3
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
./run.sh
```

Or manually: `cd app && ../.venv/bin/uvicorn main:app --reload --host 0.0.0.0 --port 8000`

### 3. Dashboard frontend

Node.js 20 is expected at `~/.local/node-v20.18.0-linux-x64/bin` (or any Node 18+ on your PATH).

```bash
cd /home/pvb/work/proj/worldcup/dashboard/frontend
npm install
./run.sh
```

Or manually: `npm run dev`

**Windows Chrome + WSL:** prefer the WSL IP if localhost fails:

```bash
hostname -I | awk '{print $1}'   # e.g. 172.22.117.148 → http://172.22.117.148:5173
```

Do **not** use `10.255.255.254` — that is WSL internal DNS, not the web app.

### Troubleshooting "connection reset" / site not loading

Both servers must be running at the same time:

1. **Backend** (terminal 1): `cd dashboard/backend && ./run.sh`
2. **Frontend** (terminal 2): `cd dashboard/frontend && ./run.sh`

Quick checks inside WSL:

```bash
curl http://127.0.0.1:8000/api/health   # should return {"status":"ok"}
curl http://127.0.0.1:5173/           # should return HTML
```

If curl works in WSL but Chrome on Windows fails on localhost:

- **Use the WSL IP** (reliable): `http://$(hostname -I | awk '{print $1}'):5173`
- **Do not use** `10.255.255.254` — not a server address
- **Fix localhost forwarding** (Windows PowerShell): `wsl --shutdown`, then reopen WSL and restart servers
- Optional `%UserProfile%\.wslconfig`:
  ```ini
  [wsl2]
  localhostForwarding=true
  ```
- Port **5173** is the webpage; port **8000** is API-only
- Restart both `./run.sh` scripts after a WSL/Windows reboot

Static fallback (no dev server):

```bash
cd dashboard/frontend && npm run build
cd ../backend/app && ../.venv/bin/uvicorn main:app --host 0.0.0.0 --port 8000
# open http://localhost:8000 only if you mount the build; dev mode uses port 5173
```

Production frontend build output: `dashboard/artifacts/build/`

## API endpoints

- `GET /api/config` — `{ "default_strength": "elo", "strength_sources": ["elo", "fifa"] }`
- `GET /api/teams/rankings?strength=elo` — cached rankings when warm (no resim)
- `POST /api/simulations` — body `{ "strength": "elo"|"fifa", "simulations": 1000 }` → `{ "job_id" }`
- `GET /api/simulations/{job_id}` — `{ "status", "progress", "message", "result?" }` (progress every 100 sims)
- `GET /api/predictions/worldcup?strength=elo`
- `GET /api/matches?year=2026`
- `GET /api/groups?year=2026`
- `GET /api/metrics`
- `POST /api/refresh-data` — force-fetch World Cup raw data, ingest, retrain Elo, re-simulate both strengths

## Data sources

| Competition | Source | Editions / cycles |
|---|---|---|
| World Cup finals | [openfootball/worldcup.json](https://github.com/openfootball/worldcup.json) | 2018, 2022, 2026 |
| UEFA Euro | [openfootball/internationals](https://github.com/openfootball/internationals) `Football.TXT` | 2020, 2024 |
| Copa América | same | 2021, 2024 |
| AFCON | same | 2021, 2023, 2025 |
| WC qualifiers | same | 2022 cycle, 2026 cycle |

Raw layout under `model/data/raw/`:

```
2018.json, 2022.json, 2026.json          # World Cup (existing schema)
euro/2020.json, 2024.json
copa_america/2021.json, 2024.json
afcon/2021.json, 2023.json, 2025.json
wc_qualifiers/2022.json, 2026.json
```

Continental/qualifier files are parsed from `Football.TXT` into the same match schema as `worldcup.json`. Match importance weights follow World Football Elo Ratings (WC finals = 1.0, continental finals = 50/60, qualifiers = 40/60) and are applied in Elo updates. Backtests and tournament simulation stay World Cup–only; training uses all competitions. The held-out backtest year is 2022 (2018 has no prior training window after dropping 2010/2014).

## Refresh during the tournament

As 2026 matches complete, click **Refresh data** in the dashboard (re-fetches World Cup JSON, then ingest/train/simulate) or run:

```bash
cd /home/pvb/work/proj/worldcup/model
python scripts/fetch_data.py --force --competitions world_cup
python scripts/ingest.py && python scripts/train.py && python scripts/simulate.py
```

Knockout scores include full-time, extra-time (`et`), and penalties (`p`) when present; the bracket page highlights who advanced and shows `aet` / `p` notes as needed.
