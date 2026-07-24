from __future__ import annotations

import json
import sys
from collections.abc import Callable
from pathlib import Path

import pandas as pd

SRC = Path(__file__).resolve().parent
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from config import (
    ARTIFACTS_PREDICTIONS,
    ARTIFACTS_TRAINING,
    DEFAULT_STAGE,
    DEFAULT_STRENGTH,
    STAGE_ORDER,
    STRENGTH_SOURCES,
)
from ingest import load_matches
from models.elo import EloModel
from models.fifa import (
    load_fifa_snapshot,
    rank_lookup,
    rank_table_from_values,
    ratings_for_strength,
)
from simulation.bracket import RealBracketSimulator, list_tournament_teams

ProgressCallback = Callable[[int, int], None]


def normalize_strength(strength: str | None) -> str:
    if strength in STRENGTH_SOURCES:
        return strength
    return DEFAULT_STRENGTH


def normalize_stage(stage: str | None) -> str:
    if stage in STAGE_ORDER:
        return stage
    return DEFAULT_STAGE


def load_stage_elo(stage: str) -> EloModel:
    path = ARTIFACTS_TRAINING / f"elo_{stage}.json"
    if path.exists():
        return EloModel.load(path)
    return EloModel.load()


def run_simulation(
    strength: str = DEFAULT_STRENGTH,
    stage: str = DEFAULT_STAGE,
    simulations: int = 3000,
    on_progress: ProgressCallback | None = None,
) -> pd.DataFrame:
    strength = normalize_strength(strength)
    stage = normalize_stage(stage)
    matches = load_matches()
    pure_elo = load_stage_elo(stage)
    simulator = RealBracketSimulator(matches, pure_elo, strength=strength, stage=stage)
    return simulator.run(simulations=simulations, on_progress=on_progress)


def build_rankings_payload(
    strength: str = DEFAULT_STRENGTH,
    stage: str = DEFAULT_STAGE,
    resimulate: bool = False,
    simulations: int = 3000,
    on_progress: ProgressCallback | None = None,
) -> dict:
    strength = normalize_strength(strength)
    stage = normalize_stage(stage)
    matches = load_matches()
    pure_elo = load_stage_elo(stage)
    fifa = load_fifa_snapshot()
    teams = list_tournament_teams(matches)
    active = ratings_for_strength(pure_elo, fifa, strength, teams=teams)

    path = ARTIFACTS_PREDICTIONS / f"worldcup_{stage}_{strength}.json"
    if resimulate or not path.exists():
        simulator = RealBracketSimulator(matches, pure_elo, strength=strength, stage=stage)
        pred_df = simulator.run(simulations=simulations, on_progress=on_progress)
        simulator.save_predictions(pred_df, simulations=simulations)
        resimulated = True
    else:
        payload = json.loads(path.read_text(encoding="utf-8"))
        pred_df = pd.DataFrame(payload.get("teams", []))
        resimulated = False

    if pred_df.empty:
        return {
            "strength": strength,
            "stage": stage,
            "fifa_snapshot": fifa.snapshot_id,
            "resimulated": resimulated,
            "teams": [],
        }

    elo_ranks = rank_table_from_values(
        {team: pure_elo.ratings.get(team, 1500.0) for team in teams}
    )
    active_ranks = rank_table_from_values(active.ratings)

    pred_df = pred_df.copy()
    pred_df = pred_df.sort_values(
        ["p_win", "rating"], ascending=[False, False]
    ).reset_index(drop=True)
    pred_df["model_rank"] = pred_df.index + 1
    model_rank_map = dict(zip(pred_df["team"], pred_df["model_rank"]))

    rows = []
    for team in sorted(teams, key=lambda t: model_rank_map.get(t, 9999)):
        if team not in model_rank_map:
            continue
        pred_row = pred_df[pred_df["team"] == team]
        if pred_row.empty:
            continue
        pred_row = pred_row.iloc[0]
        rows.append(
            {
                "team": team,
                "model_rank": int(model_rank_map[team]),
                "elo_rank": int(elo_ranks.get(team, 999)),
                "fifa_rank": int(rank_lookup(fifa, team)),
                "active_rank": int(active_ranks.get(team, 999)),
                "rating": float(pure_elo.ratings.get(team, 1500.0)),
                "active_rating": float(active.ratings.get(team, 1500.0)),
                "p_r32": float(pred_row.get("p_r32", 0.0)),
                "p_r16": float(pred_row.get("p_r16", 0.0)),
                "p_qf": float(pred_row.get("p_qf", 0.0)),
                "p_sf": float(pred_row.get("p_sf", 0.0)),
                "p_final": float(pred_row.get("p_final", 0.0)),
                "p_win": float(pred_row.get("p_win", 0.0)),
                "group": pred_row.get("group"),
                "rank": int(model_rank_map[team]),
            }
        )

    rows.sort(key=lambda r: r["model_rank"])
    return {
        "strength": strength,
        "stage": stage,
        "fifa_snapshot": fifa.snapshot_id,
        "resimulated": resimulated,
        "teams": rows,
    }
