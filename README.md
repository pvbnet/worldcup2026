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
| **Elo ratings** | Team strength updated after each match (training engine); one model per tournament-stage cutoff |
| **FIFA rankings** | Converted to pseudo-Elo for an alternate strength source |
| **Elo / FIFA toggle** | Binary switch: Monte Carlo match outcomes use either trained Elo or FIFA-based ratings |
| **Tournament stage selector** | Pins the model + simulation to "what was knowable as of stage X" (see below) |
| **Monte Carlo sim** | Simulates the real 2026 bracket forward from the selected stage → stage-reach and win probabilities |

There is a single match-outcome engine (Elo win probabilities). Strength input is either trained Elo or FIFA pseudo-Elo.

### Tournament stage selector

The dashboard (and the underlying model) can be pinned to any of seven stages, each meaning "train on and lock in results up to and including this stage; simulate everything after it":

| Stage id | Label | Fixed (real) results used | Simulated |
|---|---|---|---|
| `pre_tournament` | Pre-tournament | none | Groups → R32 → R16 → QF → SF → Final |
| `group` | Group stage done | Group stage | R32 → Final |
| `r32` | Round of 32 done | Group + R32 | R16 → Final |
| `r16` | Round of 16 done | Group + R32 + R16 | QF → Final |
| `qf` | Quarterfinals done | … + QF | SF → Final |
| `sf` | Semifinals done | … + SF | Final only |
| `complete` | Tournament complete | everything | nothing (probabilities are the real 0/1 outcome) |

Selecting a stage does three things:
- **Training**: the Elo model is retrained using only current-year World Cup match results up to that stage (`model/artifacts/training/elo_{stage}.json`); all historical/continental/qualifier data is always used.
- **Simulation**: rounds at or before the cutoff are taken from the real results; rounds after it are Monte Carlo simulated.
- **Dashboard pages**: the Groups page and knockout bracket only reveal what would have been knowable at that stage (see below).

### How the tournament is simulated (`RealBracketSimulator`)

Instead of a simplified Elo-seeded bracket, the simulator reconstructs the **real** 2026 World Cup format for every stage, including `pre_tournament`:

1. **Groups** — for `pre_tournament`, all 72 group matches are simulated from scratch; for every other stage, the real group standings are used directly.
2. **Round of 32** — resolved from group standings (real or, for `pre_tournament`, that trial's simulated standings) using FIFA's published Round-of-32 slot template and the 495-row "Annex C" best-third-place table, hardcoded in `model/data/wc2026_r32_bracket.json`. This reproduces the real 2026 Round of 32 exactly (validated at startup).
3. **Round of 16 → Quarterfinals → Semifinals → Final** — a feeder tree is derived once from the completed 2026 match data (which bracket slot's winner plays in which next-round slot). Because slot succession is fixed by the schedule, this tree correctly propagates simulated results too, not just the real ones.
4. Rounds at or before the stage cutoff use the real recorded winner; rounds after it sample a winner from the active Elo/FIFA ratings each Monte Carlo trial (draws resolved with an Elo tie-break, approximating extra time/penalties).

From many trials the dashboard reports **P(R32), P(R16), P(QF), P(SF), P(Final), P(Win WC)** (monotonic by construction). For stages ≤ the cutoff these are exactly 0 or 1 (deterministic, since they're already known); for `complete`, no simulation runs at all.

## Dashboard UI

A **Tournament stage** dropdown in the header (default: **Pre-tournament**) applies to every page:

- **Groups & teams** — group standings and team detail. Shows a placeholder instead of standings when `pre_tournament` is selected (nothing is "real" yet at that stage); a team's "Recent matches" list only shows matches within the selected stage's fixed rounds.
- **Knockout Stage** — actual 2026 knockout fixtures, masked to the selected stage: rounds at or before the cutoff show real scores; the first round after the cutoff shows the real matchup with the result hidden; further rounds show blank "TBD" placeholders.
- **Predictions** — Elo/FIFA toggle; Monte Carlo run count (1000–5000); rankings table with stage-reach probabilities and an inline win-probability bar; progress overlay while sims run; a footnote explains which stages are fixed vs. predicted for the current selection.

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
python scripts/train.py        # writes elo_{stage}.json for every stage
python scripts/simulate.py     # writes worldcup_{stage}_{strength}.json for every stage × strength
```

`fetch_data.py` accepts `--competitions` (subset) and `--force` (re-download). `ingest.py` still auto-fetches missing raw files as a fallback.

Artifacts are written to:
- `model/data/` — raw and processed match data, plus `wc2026_r32_bracket.json` (the hardcoded 2026 Round-of-32 slot template + Annex C third-place table)
- `model/artifacts/training/` — one Elo model per stage, `elo_{stage}.json` (`stage` ∈ `pre_tournament, group, r32, r16, qf, sf, complete`)
- `model/artifacts/evaluation/` — backtest metrics (Elo vs FIFA on WC 2022; always trained on data before 2022, independent of the stage selector)
- `model/artifacts/predictions/` — stage-reach and win probabilities, `worldcup_{stage}_{strength}.json`

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

- `GET /api/config` — `{ "default_strength", "strength_sources", "default_stage", "stages": [{ "id", "label" }, ...] }`
- `GET /api/teams/rankings?strength=elo&stage=pre_tournament` — cached rankings when warm (no resim); `stage` defaults to `pre_tournament`, invalid values 400
- `POST /api/simulations` — body `{ "strength": "elo"|"fifa", "stage": "pre_tournament", "simulations": 1000 }` → `{ "job_id" }`
- `GET /api/simulations/{job_id}` — `{ "status", "progress", "message", "result?" }` (progress every 100 sims)
- `GET /api/predictions/worldcup?strength=elo&stage=pre_tournament`
- `GET /api/matches?year=2026` — always the full real dataset; stage-aware masking happens client-side
- `GET /api/groups?year=2026` — always the full real dataset; stage-aware masking happens client-side
- `GET /api/metrics`
- `POST /api/refresh-data` — force-fetch World Cup raw data, ingest, retrain Elo for every stage, re-simulate every stage × strength

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

## Refresh during a tournament

As matches complete, click **Refresh data** in the dashboard (re-fetches World Cup JSON, then ingest/train/simulate) or run:

```bash
cd /home/pvb/work/proj/worldcup/model
python scripts/fetch_data.py --force --competitions world_cup
python scripts/ingest.py && python scripts/train.py && python scripts/simulate.py
```

`train.py`/`simulate.py` always (re)build artifacts for every stage in `STAGE_ORDER`; downloading new results only changes what each stage cutoff actually "knows" — training data for a stage is filtered to per-match `stage` values already present in the ingested data (see `filter_training_matches`), so re-running this pipeline mid-tournament naturally picks up newly completed rounds as they're ingested. Once the tournament ends, `complete` shows the real final outcome with no simulation.

Note: `RealBracketSimulator`'s feeder-tree construction (`build_bracket_tree`) currently assumes the **full** knockout bracket (Round of 32 through the Final) has already been played, since it derives round-to-round slot links by chaining real match participants forward. It is exercised here against the completed 2026 tournament; using the stage selector mid-tournament (before the Final has been played) would need that construction to tolerate partially-completed rounds.

Knockout scores include full-time, extra-time (`et`), and penalties (`p`) when present; the bracket page highlights who advanced and shows `aet` / `p` notes as needed.
