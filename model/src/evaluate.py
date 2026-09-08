from __future__ import annotations

import json

import numpy as np
import pandas as pd
from sklearn.metrics import brier_score_loss, log_loss

from config import ARTIFACTS_EVALUATION, BACKTEST_YEARS
from models.elo import fit_elo
from models.fifa import (
    backtest_fifa_snapshot,
    load_fifa_snapshot,
    ratings_for_strength,
    seed_ratings_from_fifa,
)


def _one_hot(outcome: int) -> np.ndarray:
    arr = np.zeros(3)
    arr[outcome] = 1.0
    return arr


def _tournament_start(matches: pd.DataFrame, test_year: int) -> pd.Timestamp:
    wc = matches[
        (matches["year"] == test_year) & (matches["competition"] == "world_cup")
    ]
    return pd.to_datetime(wc["date"]).min()


def _training_matches(matches: pd.DataFrame, test_year: int) -> pd.DataFrame:
    cutoff = _tournament_start(matches, test_year)
    dated = pd.to_datetime(matches["date"], errors="coerce")
    return matches[matches["played"] & dated.notna() & (dated < cutoff)]


def _test_matches(matches: pd.DataFrame, test_year: int) -> pd.DataFrame:
    return matches[
        (matches["year"] == test_year)
        & (matches["competition"] == "world_cup")
        & matches["played"]
    ]


def _year_metrics(matches: pd.DataFrame, test_year: int) -> dict[str, dict]:
    train_matches = _training_matches(matches, test_year)
    test_matches = _test_matches(matches, test_year)
    if train_matches.empty or test_matches.empty:
        return {}

    train_teams = pd.unique(
        pd.concat([train_matches["team1"], train_matches["team2"]], ignore_index=True)
    )
    seeds = seed_ratings_from_fifa([str(t) for t in train_teams])
    elo = fit_elo(train_matches, base_ratings=seeds)
    fifa = load_fifa_snapshot(backtest_fifa_snapshot(test_year))
    teams = list(
        pd.unique(pd.concat([test_matches["team1"], test_matches["team2"]], ignore_index=True))
    )

    year_metrics: dict[str, dict] = {}
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
        year_metrics[strength] = {
            "log_loss": ll,
            "brier": brier,
            "n_matches": len(y_true_arr),
        }
    return year_metrics


def evaluate_models(matches: pd.DataFrame, training_frame: pd.DataFrame | None = None) -> dict:
    """Backtest Elo and FIFA strength sources on WC 2022 and WC 2026."""
    del training_frame  # unused; kept for call-site compatibility

    metrics: dict[str, dict] = {
        strength: {"years": {}} for strength in ("elo", "fifa")
    }
    for year in BACKTEST_YEARS:
        year_metrics = _year_metrics(matches, year)
        for strength, values in year_metrics.items():
            metrics[strength]["years"][str(year)] = values

    for strength, payload in metrics.items():
        years = payload["years"]
        total_n = sum(int(y["n_matches"]) for y in years.values())
        if total_n == 0:
            payload["mean_log_loss"] = None
            payload["mean_brier"] = None
            continue
        payload["mean_log_loss"] = (
            sum(y["log_loss"] * y["n_matches"] for y in years.values()) / total_n
        )
        payload["mean_brier"] = (
            sum(y["brier"] * y["n_matches"] for y in years.values()) / total_n
        )

    if all(not payload["years"] for payload in metrics.values()):
        return {}

    out = ARTIFACTS_EVALUATION / "metrics.json"
    out.write_text(json.dumps(metrics, indent=2), encoding="utf-8")
    return metrics
