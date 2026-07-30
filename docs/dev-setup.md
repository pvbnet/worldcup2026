# Dev setup

Development guidelines for the model pipeline, FastAPI backend, and React frontend.

**Requirements:** Python 3.12.3 (pyenv recommended), Node.js 18+ (Node 20 recommended).

Read the [README quick start](../README.md#quick-start) first. Sections below cover the model pipeline and running components separately.

## 1. Model pipeline

```bash
cd model
pyenv local 3.12.3   # optional; use pyenv if you want 3.12.3 exactly
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

python scripts/fetch_data.py   # download World Cup + Euro/Copa/AFCON/qualifiers
python scripts/ingest.py
python scripts/train.py        # writes elo_{stage}.json for every stage
python scripts/simulate.py     # writes worldcup_{stage}_{strength}.json for every stage × strength
```

Raw layout under `model/data/raw/`:

```
2018.json, 2022.json, 2026.json          # World Cup (existing schema)
euro/2020.json, 2024.json
copa_america/2021.json, 2024.json
afcon/2021.json, 2023.json, 2025.json
wc_qualifiers/2022.json, 2026.json
```

`fetch_data.py` accepts `--competitions` (subset) and `--force` (re-download). `ingest.py` still auto-fetches missing raw files as a fallback.

Artifacts are written to:
- `model/data/` — raw and processed match data, plus `wc2026_r32_bracket.json` (the hardcoded 2026 Round-of-32 slot template + Annex C third-place table)
- `model/artifacts/training/` — one Elo model per stage, `elo_{stage}.json` (`stage` ∈ `pre_tournament, group, r32, r16, qf, sf, complete`)
- `model/artifacts/evaluation/` — backtest metrics (Elo vs FIFA on WC 2022; always trained on data before 2022, independent of the stage selector)
- `model/artifacts/predictions/` — stage-reach and win probabilities, `worldcup_{stage}_{strength}.json`

Pre-built files under `model/artifacts/` are committed so the dashboard runs without re-simulating; regenerate with `train.py` / `simulate.py` or **Refresh data** in the UI.

### Refreshing data during the World Cup tournament

Click **Refresh data** in the dashboard or run:

```bash
cd model
python scripts/fetch_data.py --force --competitions world_cup
python scripts/ingest.py && python scripts/train.py && python scripts/simulate.py
```

`train.py`/`simulate.py` always (re)build artifacts for every stage in `STAGE_ORDER`; downloading new results only changes what each stage cutoff actually "knows" — training data for a stage is filtered to per-match `stage` values already present in the ingested data (see `filter_training_matches`), so re-running this pipeline mid-tournament naturally picks up newly completed rounds as they're ingested. Once the tournament ends, `complete` shows the real final outcome with no simulation.

Note: `RealBracketSimulator`'s feeder-tree construction (`build_bracket_tree`) currently assumes the **full** knockout bracket (Round of 32 through the Final) has already been played, since it derives round-to-round slot links by chaining real match participants forward. It is exercised here against the completed 2026 tournament; using the stage selector mid-tournament (before the Final has been played) would need that construction to tolerate partially-completed rounds.

## 2. Dashboard backend

```bash
cd dashboard/backend
pyenv local 3.12.3   # optional; use pyenv if you want 3.12.3 exactly
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

## 3. Dashboard frontend

Node.js 18+ (Node 20 recommended). Local run scripts source [`scripts/env.sh`](../scripts/env.sh), which by default prepends a user-local Node install under `~/.local` when that directory exists. Edit that file — or comment out the block — if `node`/`npm` are already on your PATH (nvm, apt, fnm).

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

## 4. Local test of production build

One process serves the **built** frontend and the API at: **http://localhost:8080/**

```bash
cd dashboard/backend && ./run-prod.sh
```

Sanity checks:

```bash
curl http://localhost:8080/api/health
curl -s -o /dev/null -w "%{http_code}\n" http://localhost:8080/teams
```

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

## See also

- [README](../README.md) — overview, quick start, tournament model, UI
- [architecture.md](architecture.md) — high-level architecture and dataflow
- [scripts/env.sh](../scripts/env.sh) — Node.js PATH for local run scripts
- [docker-local.md](docker-local.md) — container build and run
- [gcp-setup.md](gcp-setup.md) — Google Cloud setup: artifact registry and cloud run
