# Evaluation of Match and Tournament Predictions

Two separate evaluations measure this project’s forecasts. **Match evaluation** scores the strength model on individual World Cup games. **Simulation evaluation** scores the Monte Carlo tournament outputs (stage-reach and win probabilities) against the realized 2026 bracket.

Match-level log-loss and Brier say whether Elo (or FIFA pseudo-Elo) assigned sensible win/draw/lose probabilities. They do not say whether the simulator’s `P(reach QF)` or `P(win)` were well calibrated. Published tournament-forecast systems (Groll/Zeileis, FiveThirtyEight SPI, Opta, ACE Lab’s 2026 comparison) report both kinds of scores.

Run both from `model/`:

```bash
python scripts/evaluate.py
```

`train.py` also reruns match evaluation after fitting Elo. 

`simulate.py` reruns simulation evaluation after writing prediction JSON. 

## 1. Match results evaluation

**Years:** 2022 and 2026 (see [`model/src/config.py`](../model/src/config.py))  
**Code:** [`model/src/evaluate_matches.py`](../model/src/evaluate_matches.py)  
**Strength inputs:** trained Elo vs FIFA pseudo-Elo

This is a proper-score backtest of three-way match probabilities (team1 win / draw / team2 win). Lower log-loss and Brier are better.

### Training window (no leakage)

Elo is fit only on **played** matches whose `date` is **strictly before** the tournament kickoff
(2022-11-20 and 2026-06-11 respectively).

Rows with missing or unparseable dates are dropped from training. Elo initial ratings still come from the FIFA **tuning** snapshot (`2017-12`), which sits before the training window.

During the test tournament, ratings are **frozen**. Each WC match is scored with match probabilities from those pre-tournament ratings (or from FIFA pseudo-Elo). Outcomes use full-time goals only (0 = team1 win, 1 = draw, 2 = team2 win).

Likewise, the FIFA comparison model uses a ranking published prior to the tournament.

### Metrics

For each strength source and year:

- **Log-loss** — multiclass `sklearn.metrics.log_loss` over labels `{0, 1, 2}`
- **Brier** — mean of the three-way Brier score (one-hot outcome vs predicted probabilities)
- **n_matches** — 64 in 2022, 104 in 2026

`mean_log_loss` and `mean_brier` are **n_matches-weighted** averages across years.

**Output:** [`model/artifacts/evaluation/match_metrics.json`](../model/artifacts/evaluation/match_metrics.json)  

```json
{
  "elo": {
    "years": {
      "2022": { "log_loss": 1.021, "brier": 0.204, "n_matches": 64 },
      "2026": { "log_loss": 0.956, "brier": 0.185, "n_matches": 104 }
    },
    "mean_log_loss": 0.981,
    "mean_brier": 0.192
  },
  "fifa": { }
}
```

`GET /api/metrics` returns this file.

## 2. Tournament simulation evaluation

**Code:** [`model/src/evaluate_simulation.py`](../model/src/evaluate_simulation.py)  
**Year:** 2026 only  
**Inputs:** committed [`model/artifacts/predictions/worldcup_{stage}_{strength}.json`](../model/artifacts/predictions/) files — the same forecasts the dashboard shows

This scores the **tournament simulator**, not the per-match engine.

### Realized 2026 outcomes

From played 2026 `world_cup` knockout rows (`stage` in `r32, r16, qf, sf, final`): a team **reached** that round if it appears in a fixture. The champion is the `advancer` of the played final (same extra-time/penalty rule as ingest). Expected counts: 32 / 16 / 8 / 4 / 2 / 1.

### Vintages and unresolved events

Each prediction file conditions on realized results through that cutoff (and uses the matching `elo_{stage}.json`). Locked rounds are omitted from Brier/log-loss:

| Vintage | Score these |
|---------|-------------|
| `pre_tournament` | r32, r16, qf, sf, final, win |
| `group` | r16, qf, sf, final, win |
| `r32` | qf, sf, final, win |
| `r16` | sf, final, win |
| `qf` | final, win |
| `sf` | win |

`complete` is skipped (everything is known).

### Metrics

Each vintage scores only its unresolved events. Lower Brier, log-loss, and TRPS are better; higher skill is better.

**Brier** — `(p − y)²` for each team and event, with `y` in `{0, 1}`. Per-event `brier` is the mean over all 48 teams. `mean_brier` averages those event scores. `mean_brier_from_qf` is the same average restricted to `qf`, `sf`, `final`, and `win`. Each `teams[]` row stores that team’s mean over the vintage’s events. Top-level `tournament_mean_brier` copies the pre-tournament Elo and FIFA aggregates.

Note: Averaging Brier score over reach events is equivalent to the Ranked Probability Score (RPS) used by [ACE Lab’s 2026 model comparison](https://ac3lab.github.io/blog/2026/model_comparison_en/). We store it as `mean_brier` rather than a separate `rps` field.

**Log-loss** — binary `−[y log p + (1 − y) log(1 − p)]`, with `p` clipped to `[1e-15, 1 − 1e-15]`. The same averaging as Brier: per-event `log_loss`, then `mean_log_loss`, `mean_log_loss_from_qf`, per-team rows, and top-level `tournament_mean_log_loss`.

**Baseline and skill** — remaining teams share remaining slots equally (pre-tournament `p_win = 1/48`; after groups, the 32 survivors share `p_r16 = 16/32`; and so on). Eliminated teams have baseline 0. `mean_brier_baseline` / `mean_log_loss_baseline` (and the `_from_qf` variants) use those probabilities. Skill is `1 − score / baseline` on the unresolved-event mean (`brier_skill`, `log_loss_skill`). Positive skill means the forecast beat equal-share chance.

**TRPS** — Tournament Rank Probability Score (Ekstrøm et al., eq. 2). Reach probabilities are converted to seven partial-rank masses (2026 slot sizes 1 / 1 / 2 / 4 / 8 / 16 / 16):

- `P(champion) = p_win`
- `P(runner-up) = p_final − p_win`
- `P(sf_exit) = p_sf − p_final`
- `P(qf_exit) = p_qf − p_sf`
- `P(r16_exit) = p_r16 − p_qf`
- `P(r32_exit) = p_r32 − p_r16`
- `P(group_exit) = 1 − p_r32`

Tiny negative diffs from Monte Carlo noise are clipped to 0 and the column is renormalized. TRPS is the mean over teams of the mean squared CDF error on that ranking. Zero is perfect. Unlike Brier/log-loss, TRPS still uses the full ranking at every vintage.

**Output:** [`model/artifacts/evaluation/simulation_metrics.json`](../model/artifacts/evaluation/simulation_metrics.json)  

## See also

- [architecture.md](architecture.md) — artifacts and data flow
