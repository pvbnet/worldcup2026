# World Cup 2026 Predictive Dashboard

Interactive dashboard ranking national soccer teams and estimating 2026 World Cup win probabilities. 
Uses game data from previous World Cup finals, continental tournaments (Euro, Copa América, AFCON), 
and World Cup qualifiers for predicting team strength (Elo rating). Uses Monte-Carlo simulations of 
the 2026 tournament to predict the probabilities of teams reaching knock-out stages and the 
final WC 2026 tournament winner. 

Game results from the actual 2026 World Cup tournament are used as they become available, per the main
stages. The dashboard can be pinned to lock in results from played stages, and past results are used to
update the Elo rating and knock-out stage win probabilities by Monte-Carlo simulations of the remaining 
tournament. 

## Quick start

**Requirements:** Python 3.12.3 (pyenv recommended), Node.js 18+ (20 recommended).

```bash
git clone https://github.com/pvbnet/worldcup2026.git
# SSH: git clone git@github.com:pvbnet/worldcup2026.git
cd worldcup2026
```

Configure Node via [`scripts/env.sh`](scripts/env.sh) if `node` is not already on your PATH.

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
./start-dashboard-local.sh
```

Open **http://localhost:5173/** in the browser.

## Documentation

- [docs/architecture.md](docs/architecture.md) — components, runtime modes, data flow
- [docs/dev-setup.md](docs/dev-setup.md) — model pipeline, backend, frontend, API, prod-local test
- [docs/docker-local.md](docs/docker-local.md) — build and run the container locally
- [docs/gcp-setup.md](docs/gcp-setup.md) — deploy to Cloud Run

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

Knockout scores include full-time scores and results from extra-time (`aet`), and penalties (`p`) when present.

As matches complete during the tournament, click **Refresh data** in the dashboard (re-fetches World Cup JSON, then ingest/train/simulate). This can also be done manually using the Python scripts. 

## Data sources

See [NOTICE.md](NOTICE.md) for third-party data licensing and what is (and is not) committed to git.

| Competition | Source | Editions / cycles |
|---|---|---|
| World Cup finals | [openfootball/worldcup.json](https://github.com/openfootball/worldcup.json) | 2018, 2022, 2026 |
| UEFA Euro | [openfootball/internationals](https://github.com/openfootball/internationals) `Football.TXT` | 2020, 2024 |
| Copa América | same | 2021, 2024 |
| AFCON | same | 2021, 2023, 2025 |
| WC qualifiers | same | 2022 cycle, 2026 cycle |

## License

MIT — see [LICENSE](LICENSE). Third-party data terms are described in [NOTICE.md](NOTICE.md).

Contributing: [CONTRIBUTING.md](CONTRIBUTING.md). Security: [SECURITY.md](SECURITY.md).
