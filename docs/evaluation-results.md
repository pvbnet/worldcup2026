# Evaluation results

Scores for the 2026 World Cup forecasts in this repo. Metric definitions: [evaluation.md](evaluation.md). 

Match and simulation numbers come from committed `match_metrics.json` and `simulation_metrics.json`. ACE Laboratory rows are transcribed from [their 2026 model comparison](https://ac3lab.github.io/blog/2026/model_comparison_en/) (Figures 3–5). Regenerate with `python scripts/write_evaluation_md.py` from `model/`.

Lower Brier, RPS, and log-loss are better. Per-stage columns are Brier scores. RPS is the average of those Briers (R32 through champion), matching ACE’s tournament RPS; RPS QF→ averages QF through champion. Log-loss columns use the same averaging.

## All-match evaluation

Pre-tournament strength models scored on all World Cup matches (three-way win/draw/lose).

| Model | 2022 log-loss | 2022 Brier | 2026 log-loss | 2026 Brier |
| :--- | :---: | :---: | :---: | :---: |
| FIFA | 1.0194 | 0.2033 | 1.0046 | 0.1978 |
| Elo | 1.0211 | 0.2036 | 0.9562 | 0.1848 |

## Full tournament simulation results

Naive baseline is equal-share chance (each of the 48 teams has probability *k*/48 of occupying one of *k* remaining slots). Our sim rows use pre-tournament Monte Carlo results. Stage columns are Brier; RPS is average Brier. 

| Model | Brier R32 | Brier R16 | Brier QF | Brier SF | Brier Final | Brier Win | │ | RPS (avg Brier) | RPS QF→ | Log-loss | Log-loss QF→ |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| Naive baseline | 0.2222 | 0.2222 | 0.1389 | 0.0764 | 0.0399 | 0.0204 | │ | 0.1200 | 0.0689 | 0.3808 | 0.2530 |
| Our sim - FIFA | 0.2122 | 0.1810 | 0.1127 | 0.0590 | 0.0346 | 0.0183 | │ | 0.1030 | 0.0562 | 0.3216 | 0.1934 |
| Our sim - Elo | 0.2018 | 0.1610 | 0.0974 | 0.0506 | 0.0290 | 0.0173 | │ | 0.0929 | 0.0486 | 0.2893 | 0.1648 |
| ACE Classic | 0.1277 | 0.1233 | 0.0944 | 0.0500 | 0.0300 | 0.0166 | │ | 0.0733 | 0.0476 | 0.2377 | 0.1577 |
| ACE Bayesian | 0.1666 | 0.1466 | 0.0888 | 0.0444 | 0.0277 | 0.0144 | │ | 0.0801 | 0.0433 | 0.2534 | 0.1445 |

The following diagram shows the same results in a color-coded visual grid.
The color scale is column-wise (green = best / lowest among shown models).

![Pre-tournament simulation scores](evaluation-headline.svg)

## Per-team RPS (Our sim - Elo)

Pre-tournament Elo simulation scored per country. Stage columns are that team’s Brier for each reach event. RPS is the average of those Briers (R32 through champion); RPS QF→ averages QF through champion. Teams are ordered by Elo rank. Color scale is column-wise (green = best / lowest among the 48 teams).

![Per-team Elo simulation RPS](evaluation-elo-teams.svg)
