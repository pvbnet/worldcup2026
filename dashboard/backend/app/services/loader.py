from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[4]
MODEL_ROOT = PROJECT_ROOT / "model"
MODEL_SRC = MODEL_ROOT / "src"
ARTIFACTS_TRAINING = MODEL_ROOT / "artifacts" / "training"
ARTIFACTS_PREDICTIONS = MODEL_ROOT / "artifacts" / "predictions"
ARTIFACTS_EVALUATION = MODEL_ROOT / "artifacts" / "evaluation"
DATA_PROCESSED = MODEL_ROOT / "data" / "processed"

if str(MODEL_SRC) not in sys.path:
    sys.path.insert(0, str(MODEL_SRC))

from config import DEFAULT_STAGE, STAGE_LABELS, STAGE_ORDER  # noqa: E402
from rankings_api import (  # noqa: E402
    ProgressCallback,
    build_rankings_payload,
    normalize_stage,
    normalize_strength,
)


def load_predictions(strength: str = "elo", stage: str = DEFAULT_STAGE) -> dict:
    strength = normalize_strength(strength)
    stage = normalize_stage(stage)
    path = ARTIFACTS_PREDICTIONS / f"worldcup_{stage}_{strength}.json"
    if not path.exists():
        return {"strength": strength, "stage": stage, "teams": [], "simulations": 0}
    return json.loads(path.read_text(encoding="utf-8"))


def load_rankings(
    strength: str = "elo",
    stage: str = DEFAULT_STAGE,
    resimulate: bool = False,
    simulations: int = 3000,
    on_progress: ProgressCallback | None = None,
) -> dict:
    return build_rankings_payload(
        strength=strength,
        stage=stage,
        resimulate=resimulate,
        simulations=simulations,
        on_progress=on_progress,
    )


def load_config() -> dict:
    return {
        "default_strength": "elo",
        "strength_sources": ["elo", "fifa"],
        "default_stage": DEFAULT_STAGE,
        "stages": [{"id": stage, "label": STAGE_LABELS[stage]} for stage in STAGE_ORDER],
    }


def load_matches(year: int | None = None, played: bool | None = None) -> list[dict]:
    path = DATA_PROCESSED / "matches.parquet"
    if not path.exists():
        return []
    df = pd.read_parquet(path)
    if "competition" in df.columns:
        df = df[df["competition"] == "world_cup"]
    if year is not None:
        df = df[df["year"] == year]
    if played is not None:
        df = df[df["played"] == played]
    return df.sort_values(["date", "year"]).to_dict(orient="records")


def load_metrics() -> dict:
    path = ARTIFACTS_EVALUATION / "metrics.json"
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def load_elo_ratings(stage: str = "pre_tournament") -> dict[str, float]:
    path = ARTIFACTS_TRAINING / f"elo_{stage}.json"
    if not path.exists():
        return {}
    payload = json.loads(path.read_text(encoding="utf-8"))
    return payload.get("ratings", {})


def group_standings(year: int = 2026) -> dict[str, list[dict]]:
    matches = pd.DataFrame(load_matches(year=year, played=True))
    if matches.empty:
        return {}
    groups: dict[str, list[dict]] = {}
    for group, gm in matches.groupby("group"):
        if pd.isna(group):
            continue
        table: dict[str, dict] = {}
        for _, row in gm.iterrows():
            for team, gf, ga in (
                (row["team1"], row["goals1"], row["goals2"]),
                (row["team2"], row["goals2"], row["goals1"]),
            ):
                table.setdefault(
                    team,
                    {
                        "team": team,
                        "played": 0,
                        "wins": 0,
                        "draws": 0,
                        "losses": 0,
                        "gf": 0,
                        "ga": 0,
                        "points": 0,
                        "gd": 0,
                    },
                )
                st = table[team]
                st["played"] += 1
                st["gf"] += int(gf)
                st["ga"] += int(ga)
                if gf > ga:
                    st["wins"] += 1
                elif gf < ga:
                    st["losses"] += 1
                else:
                    st["draws"] += 1
        for st in table.values():
            st["points"] = st["wins"] * 3 + st["draws"]
            st["gd"] = st["gf"] - st["ga"]
        groups[str(group)] = sorted(
            table.values(),
            key=lambda s: (s["points"], s["gd"], s["gf"], s["team"]),
            reverse=True,
        )
    return groups


def refresh_pipeline() -> dict:
    model_dir = MODEL_ROOT
    steps = [
        [sys.executable, "scripts/fetch_data.py", "--force", "--competitions", "world_cup"],
        [sys.executable, "scripts/ingest.py"],
        [sys.executable, "scripts/train.py"],
        [sys.executable, "scripts/simulate.py"],
    ]
    for cmd in steps:
        subprocess.run(cmd, cwd=model_dir, check=True)
    return {
        "status": "ok",
        "message": "World Cup data fetched, ingested, Elo trained, simulations updated.",
    }
