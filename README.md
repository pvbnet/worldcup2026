# World Cup 2026 Predictive Dashboard

Interactive dashboard ranking national soccer teams and estimating 2026 World Cup win probabilities. 
Uses game data from previous World Cup finals (2018, 2022) plus continental tournaments (Euro, Copa América, AFCON) 
and World Cup qualifiers for predicting team strength (Elo rating). Uses Monte-Carlo simulations of the 2026 tournament 
to predict the probabilities of teams reaching knock-out stages and the final WC 2026 tournament winner. 

Game results from the actual 2026 World Cup tournament are used as they become available, per the main
stages. The dashboard can be pinned to lock in results from played stages, and past results are used to
update the Elo rating and knock-out stage win probabilities by Monte-Carlo simulations of the remaining 
tournament. 

## Quick start

**Requirements:** Python 3.12.3 (pyenv recommended), Node.js 18+.

```bash
git clone https://github.com/pvbnet/worldcup2026.git
# SSH: git clone git@github.com:pvbnet/worldcup2026.git
cd worldcup2026
```

For detailed instructions on setting up Python environments, the model, the backend, and the frontend, see the [dev setup section](#dev-setup).

To start the dashboard backend and frontend from the repo root:

```bash
./start-dashboard-local.sh
```

Open **http://localhost:5173/** in the browser.

## Project layout

```
worldcup2026/
  model/          # data ingest, Elo training, evaluation, simulation
  dashboard/      # dashboard
    backend/      # FastAPI backend
    frontend/     # React/Vite frontend
    artifacts/    # compiled website files
```

High-level system design: [docs/architecture.md](docs/architecture.md).

## Team strength and match outcome model

| Piece | Purpose |
|---|---|
| **Elo ratings** | Team strength updated after each match (training engine) |
| **FIFA rankings** | Alternate, public, strength ranking (converted to pseudo-Elo) |
| **Elo / FIFA toggle** | Binary switch: simulations use either trained Elo or FIFA-based ratings |
| **Stage completed** control | Pins the model + simulation to "what was knowable as of stage X" (see below) |
| **Monte Carlo sim** | Simulates the 2026 bracket forward from the selected stage → stage-reach and win probabilities |

There is a single match-outcome engine: Elo win probabilities (either trained or from FIFA ranking).

### Tournament stage selector

The dashboard (and the underlying model) can be pinned to any of the stages completed (played), each meaning "train on and lock in known results up to and including this stage; simulate everything after it":

| Stage id | Label | Fixed (real) results used | Simulated |
|---|---|---|---|
| `pre_tournament` | Pre-tournament | none | Groups → R32 → R16 → QF → SF → Final |
| `group` | Group stage done | Group stage | R32 → Final |
| `r32` | Round of 32 done | Group + R32 | R16 → Final |
| `r16` | Round of 16 done | Group + R32 + R16 | QF → Final |
| `qf` | Quarterfinals done | … + QF | SF → Final |
| `sf` | Semifinals done | … + SF | Final only |
| `complete` | Tournament complete | everything | nothing (probabilities are the real 0/1 outcome) |

### How the tournament is simulated

The simulator reconstructs the 2026 World Cup format for every stage:

1. **Groups** — for `pre_tournament`, all 72 group matches are simulated from scratch; for every other stage, the real group standings are used directly.
2. **Round of 32** — resolved from group standings (real or, for `pre_tournament`, that trial's simulated standings) using FIFA's published Round-of-32 slot template and best-third-place table.
3. **Round of 16 → Quarterfinals → Semifinals → Final** — a feeder tree is derived once from the completed 2026 match data. This tree correctly propagates simulated results as well as the real ones.
4. Rounds at or before the stage cutoff use the real recorded winner; rounds after it sample a winner from the active Elo/FIFA ratings each Monte Carlo trial (draws resolved with an Elo tie-break, approximating extra time/penalties).

From many trials the dashboard reports **P(R32), P(R16), P(QF), P(SF), P(Final), P(Win WC)**. For stages ≤ the cutoff these are exactly 0 or 1 (deterministic, since they're already known).

## Dashboard UI

A **Stage completed (played)** control in the header (default: **Pre-tournament**) applies to every page.

- **Predictions** — Elo/FIFA toggle; Monte Carlo run count (1000–5000, default **3000**); rankings table with stage-reach probabilities and an inline win-probability bar; progress overlay while sims run; a footnote explains which stages are fixed vs. predicted for the current selection.
- **Teams & groups** — group standings and team detail. A team's "Recent matches" list shows matches within the selected stage's played rounds.
- **Knockout Stage** — actual 2026 knockout fixtures, masked to the selected stage: rounds at or before the cutoff show real scores; the first round after the cutoff shows the real matchup with the result hidden; further rounds show placeholders.

## Dev Setup

Uses **pyenv** (Python 3.12.3) with local virtualenvs in each component.

### 1. Model pipeline

```bash
cd model
pyenv local 3.12.3
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

python scripts/fetch_data.py   # download World Cup + Euro/Copa/AFCON/qualifiers
python scripts/ingest.py
python scripts/train.py        # writes elo_{stage}.json for every stage
python scripts/simulate.py     # writes worldcup_{stage}_{strength}.json for every stage × strength
```

`fetch_data.py` accepts `--competitions` (subset) and `--force` (re-download). `ingest.py` still auto-fetches missing raw files as a fallback.

Artifacts are written to:
- `model/data/` — raw and processed match data, plus `wc2026_r32_bracket.json` (the hardcoded 2026 Round-of-32 slot template + Annex C third-place table)
- `model/artifacts/training/` — one Elo model per stage, `elo_{stage}.json` (`stage` ∈ `pre_tournament, group, r32, r16, qf, sf, complete`)
- `model/artifacts/evaluation/` — backtest metrics (Elo vs FIFA on WC 2022; always trained on data before 2022, independent of the stage selector)
- `model/artifacts/predictions/` — stage-reach and win probabilities, `worldcup_{stage}_{strength}.json`

Pre-built files under `model/artifacts/` are committed so the dashboard runs without re-simulating; regenerate with `train.py` / `simulate.py` or **Refresh data** in the UI.

### 2. Dashboard backend

```bash
cd dashboard/backend
pyenv local 3.12.3
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Local test of dev API (at **http://localhost:8000**, auto-reload enabled):

```bash
cd dashboard/backend
./run.sh
# health check
curl http://localhost:8000/api/health
```

### 3. Dashboard frontend

Node.js 18+ on your PATH (Node 20 recommended).

Local dev test (using Vite):

```bash
cd dashboard/frontend
npm install
./run.sh        # Runs `npm run dev`
curl http://localhost:5173/
```

Open dashboard at: **http://localhost:5173/**

Generate production build:

```bash
cd dashboard/frontend && ./build.sh
```

The production frontend build output is located at: `dashboard/artifacts/build/`

### 4. Local test of production build

One process serves the **built** frontend and the API at: **http://localhost:8080/**

```bash
cd dashboard/backend && ./run-prod.sh
```

Sanity checks:

```bash
curl http://localhost:8080/api/health
curl -s -o /dev/null -w "%{http_code}\n" http://localhost:8080/teams
```

### WSL and Windows Chrome (optional)

Skip this if **localhost / 127.0.0.1 work in your browser**. When Chrome on Windows cannot reach a server running in WSL, try `http://$(hostname -I | awk '{print $1}'):PORT` (same port as usual). 

Avoid `10.255.255.254` (WSL DNS, not the app). 

Reset forwarding: `wsl --shutdown` in PowerShell, reopen WSL, restart servers. Optional `%UserProfile%\.wslconfig`: `localhostForwarding=true` under `[wsl2]`.

## API endpoints

- `GET /api/config` — `{ "default_strength", "strength_sources", "default_stage", "stages": [{ "id", "label" }, ...] }`
- `GET /api/teams/rankings?strength=elo&stage=pre_tournament` — cached rankings when warm (no resim); `stage` defaults to `pre_tournament`, invalid values 400
- `POST /api/simulations` — body `{ "strength": "elo"|"fifa", "stage": "pre_tournament", "simulations": 3000 }` → `{ "job_id" }`
- `GET /api/simulations/{job_id}` — `{ "status", "progress", "message", "result?" }` (progress every 100 sims)
- `GET /api/predictions/worldcup?strength=elo&stage=pre_tournament`
- `GET /api/matches?year=2026` — always the full real dataset; stage-aware masking happens client-side
- `GET /api/groups?year=2026` — always the full real dataset; stage-aware masking happens client-side
- `GET /api/metrics`
- `POST /api/refresh-data` — force-fetch World Cup raw data, ingest, retrain Elo for every stage, re-simulate every stage × strength

## Data sources

See [NOTICE.md](NOTICE.md) for third-party data licensing and what is (and is not) committed to git.

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

## Refresh during a tournament

As matches complete, click **Refresh data** in the dashboard (re-fetches World Cup JSON, then ingest/train/simulate) or run:

```bash
cd model
python scripts/fetch_data.py --force --competitions world_cup
python scripts/ingest.py && python scripts/train.py && python scripts/simulate.py
```

`train.py`/`simulate.py` always (re)build artifacts for every stage in `STAGE_ORDER`; downloading new results only changes what each stage cutoff actually "knows" — training data for a stage is filtered to per-match `stage` values already present in the ingested data (see `filter_training_matches`), so re-running this pipeline mid-tournament naturally picks up newly completed rounds as they're ingested. Once the tournament ends, `complete` shows the real final outcome with no simulation.

Note: `RealBracketSimulator`'s feeder-tree construction (`build_bracket_tree`) currently assumes the **full** knockout bracket (Round of 32 through the Final) has already been played, since it derives round-to-round slot links by chaining real match participants forward. It is exercised here against the completed 2026 tournament; using the stage selector mid-tournament (before the Final has been played) would need that construction to tolerate partially-completed rounds.

Knockout scores include full-time, extra-time (`et`), and penalties (`p`) when present; the bracket page highlights who advanced and shows `aet` / `p` notes as needed.


## Deploying on Google Cloud

The intended target for deployment combines the React SPA and FastAPI backend into a single Cloud Run service for simplicity. The architecture could later be split into separate frontend and backend services if independent scaling or deployment became necessary.

Minimal one-time GCP project setup (APIs, Artifact Registry, Cloud Run deploy commands): [docs/gcp-setup.md](docs/gcp-setup.md).


## License

MIT — see [LICENSE](LICENSE). Third-party data terms are described in [NOTICE.md](NOTICE.md).

Contributing: [CONTRIBUTING.md](CONTRIBUTING.md). Security: [SECURITY.md](SECURITY.md).
