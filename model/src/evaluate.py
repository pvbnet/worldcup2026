from __future__ import annotations

import json

import numpy as np
import pandas as pd
from sklearn.metrics import brier_score_loss, log_loss

from config import ARTIFACTS_EVALUATION
from models.elo import fit_elo
from models.fifa import load_fifa_snapshot, ratings_for_strength, seed_ratings_from_fifa


def _one_hot(outcome: int) -> np.ndarray:
    arr = np.zeros(3)
    arr[outcome] = 1.0
    return arr


def evaluate_models(matches: pd.DataFrame, training_frame: pd.DataFrame | None = None) -> dict:
    """Backtest Elo and FIFA strength sources on WC 2022."""
    del training_frame  # unused; kept for call-site compatibility
    year = 2022
    if "competition" in matches.columns:
        train_matches = matches[matches["year"] < year]
        test_matches = matches[
            (matches["year"] == year)
            & (matches["competition"] == "world_cup")
            & matches["played"]
        ]
    else:
        train_matches = matches[matches["year"] < year]
        test_matches = matches[(matches["year"] == year) & matches["played"]]

    metrics: dict[str, dict] = {}
    if train_matches.empty or test_matches.empty:
        return metrics

    train_teams = pd.unique(
        pd.concat([train_matches["team1"], train_matches["team2"]], ignore_index=True)
    )
    seeds = seed_ratings_from_fifa([str(t) for t in train_teams])
    elo = fit_elo(train_matches, base_ratings=seeds)
    fifa = load_fifa_snapshot()
    teams = list(
        pd.unique(pd.concat([test_matches["team1"], test_matches["team2"]], ignore_index=True))
    )

    for strength in ("elo", "fifa"):
        model = ratings_for_strength(elo, fifa, strength, teams=[str(t) for t in teams])
        y_true = []
        prob_rows = []
        for _, row in test_matches.iterrows():
            t1, t2 = row["team1"], row["team2"]
            g1, g2 = int(row["goals1"]), int(row["goals2"])
            if g1 > g2:
                outcome = 0
            elif g1 < g2:
                outcome = 2
            else:
                outcome = 1
            y_true.append(outcome)
            probs = model.match_probs(t1, t2)
            prob_rows.append([probs["team1"], probs["draw"], probs["team2"]])

        y_true_arr = np.array(y_true)
        prob_arr = np.array(prob_rows)
        ll = float(log_loss(y_true_arr, prob_arr, labels=[0, 1, 2]))
        brier = float(
            np.mean(
                [
                    brier_score_loss(_one_hot(y), prob_arr[i])
                    for i, y in enumerate(y_true_arr)
                ]
            )
        )
        metrics[strength] = {
            "years": {
                str(year): {
                    "log_loss": ll,
                    "brier": brier,
                    "n_matches": len(y_true_arr),
                }
            },
            "mean_log_loss": ll,
            "mean_brier": brier,
        }

    out = ARTIFACTS_EVALUATION / "metrics.json"
    out.write_text(json.dumps(metrics, indent=2), encoding="utf-8")
    return metrics
