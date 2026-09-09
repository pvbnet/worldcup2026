# World Cup 2026 Predictive Dashboard

Interactive dashboard ranking national soccer teams and estimating 2026 World Cup win probabilities. 
Uses past game data to predict team strength (Elo rating). Uses Monte-Carlo simulations of 
the 2026 tournament to predict the probabilities of teams reaching knock-out stages and winning the tournament. 

The site is deployed using the Google Cloud Platform (Firebase Hosting and Cloud Run)
and live at: https://worldcup2026-dashboard.web.app/

## Team strength and match outcome model

There is a single match-outcome engine: Elo win probabilities (either trained or from FIFA ranking).

| Piece | Purpose |
|---|---|
| **Elo ratings** | Team strength updated after each match (training engine) |
| **FIFA rankings** | Alternate, public, strength ranking (converted to pseudo-Elo) |
| **Monte Carlo sim** | Simulates the 2026 bracket forward from the selected stage → stage-reach and win probabilities |

### Tournament stage selector

The simulations and dashboard can be pinned to any of the stages completed (played), each meaning "train on and lock in known results up to and including this stage; simulate everything after it":

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

1. **Groups** — all 72 group matches are simulated from scratch.
2. **Round of 32** — resolved from group standings following FIFA's published Round-of-32 slot template and best-third-place table.
3. **Round of 16 → Quarterfinals → Semifinals → Final** — a feeder tree is derived once from the completed 2026 match data. This tree correctly propagates simulated results as well as the real ones.

Rounds at or before the selected stage cutoff use the real recorded winner; rounds after it sample a winner from the active Elo/FIFA ratings each Monte Carlo trial.

From many trials the dashboard reports **P(R32), P(R16), P(QF), P(SF), P(Final), P(Win WC)**. For stages ≤ the cutoff these are exactly 0 or 1 (deterministic, since they're already known).

## Dashboard UI

Main pages: **Predictions**, **Teams & groups**, **Knockout Stage**.

A **Stage completed (played)** control in the header (default: **Pre-tournament**) applies to every page.

- **Predictions** — Elo/FIFA toggle; Monte Carlo control (**Cached** by default, or 2500 / 5000 / 10000 / 25000 / 50000 live runs). Cached loads the committed 10,000-run artifacts; choosing a count re-simulates the current stage now. Changing stage snaps back to Cached. Rankings table shows stage-reach probabilities.
- **Teams & groups** — group standings and team detail. A team's "Recent matches" list shows matches within the selected stage's played rounds.
- **Knockout Stage** — actual 2026 knockout fixtures, masked to the selected stage: rounds at or before the cutoff show real scores; later rounds show placeholders. Knockout scores include full-time scores and results from extra-time (`aet`), and penalties (`p`) when present.

## Data sources

| Competition | Source | Editions / cycles |
|---|---|---|
| World Cup finals | [openfootball/worldcup.json](https://github.com/openfootball/worldcup.json) | 2018, 2022, 2026 |
| UEFA Euro | [openfootball/internationals](https://github.com/openfootball/internationals) `Football.TXT` | 2020, 2024 |
| Copa América | same | 2021, 2024 |
| AFCON | same | 2021, 2023, 2025 |
| WC qualifiers | same | 2022 cycle, 2026 cycle |

## Quick start for development

**Requirements:** Python 3.12.3 (pyenv recommended), Node.js 18+ (20 recommended).

```bash
git clone https://github.com/pvbnet/worldcup2026.git
# SSH: git clone git@github.com:pvbnet/worldcup2026.git
cd worldcup2026
```

Configure Node via [`dashboard/env.sh`](dashboard/env.sh) if `node` is not already on your PATH.

Set up the backend and frontend dependencies:

```bash
cd dashboard/backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

cd ../frontend
npm install
```

Start the dashboard from the repo root:

```bash
./dashboard/run-dev.sh
```

Open **http://localhost:5173/** in the browser.

## Documentation

- [docs/predictions.md](docs/predictions.md) — pre-tournament rankings and stage-reach probabilities
- [docs/evaluation.md](docs/evaluation.md) — predictions evaluation methodology
- [docs/architecture.md](docs/architecture.md) — overview of components, runtime modes, data flow
- [docs/dev-setup.md](docs/dev-setup.md) — development setup, model pipeline, backend, frontend, API
- [docs/docker-local.md](docs/docker-local.md) — how to build and run the Docker container locally
- [docs/gcp-setup.md](docs/gcp-setup.md) — how to deploy to Cloud Run using the Docker image
- [docs/firebase-hosting.md](docs/firebase-hosting.md) — how to deploy to Firebase Hosting

## License and third-party data

MIT — see [LICENSE](LICENSE). Third-party data terms are described in [NOTICE.md](NOTICE.md).
