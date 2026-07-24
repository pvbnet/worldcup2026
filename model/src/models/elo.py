from __future__ import annotations

import json
from dataclasses import dataclass

import numpy as np
import pandas as pd

from config import ARTIFACTS_TRAINING


@dataclass
class EloModel:
    ratings: dict[str, float]
    k_factor: float = 32.0
    home_advantage: float = 0.0

    def expected_score(self, rating_a: float, rating_b: float) -> float:
        return 1.0 / (1.0 + 10 ** ((rating_b - rating_a) / 400.0))

    def match_probs(self, team1: str, team2: str) -> dict[str, float]:
        r1 = self.ratings.get(team1, 1500.0)
        r2 = self.ratings.get(team2, 1500.0)
        e1 = self.expected_score(r1 + self.home_advantage, r2)
        e2 = 1.0 - e1
        draw = 0.25 * (1.0 - abs(e1 - e2))
        win1 = max(0.0, e1 - draw / 2)
        win2 = max(0.0, e2 - draw / 2)
        total = win1 + draw + win2
        return {"team1": win1 / total, "draw": draw / total, "team2": win2 / total}

    def save(self, path=None) -> None:
        path = path or ARTIFACTS_TRAINING / "elo.json"
        payload = {
            "k_factor": self.k_factor,
            "home_advantage": self.home_advantage,
            "ratings": self.ratings,
        }
        path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    @classmethod
    def load(cls, path=None) -> "EloModel":
        path = path or ARTIFACTS_TRAINING / "elo.json"
        payload = json.loads(path.read_text(encoding="utf-8"))
        return cls(
            ratings=payload["ratings"],
            k_factor=payload.get("k_factor", 32.0),
            home_advantage=payload.get("home_advantage", 0.0),
        )


def fit_elo(
    matches: pd.DataFrame,
    base_rating: float = 1500.0,
    base_ratings: dict[str, float] | None = None,
) -> EloModel:
    model = EloModel(ratings={}, home_advantage=0.0)
    played = matches[matches["played"]].sort_values(["date", "year"])

    teams = pd.unique(
        pd.concat([played["team1"], played["team2"]], ignore_index=True)
    )
    for team in teams:
        model.ratings[str(team)] = (base_ratings or {}).get(str(team), base_rating)

    for _, row in played.iterrows():
        t1, t2 = row["team1"], row["team2"]
        g1, g2 = int(row["goals1"]), int(row["goals2"])
        weight = float(row["weight"]) if "weight" in row and pd.notna(row["weight"]) else 1.0
        k = model.k_factor * weight
        r1 = model.ratings[t1]
        r2 = model.ratings[t2]
        e1 = model.expected_score(r1, r2)
        if g1 > g2:
            s1, s2 = 1.0, 0.0
        elif g1 < g2:
            s1, s2 = 0.0, 1.0
        else:
            s1, s2 = 0.5, 0.5
        model.ratings[t1] = r1 + k * (s1 - e1)
        model.ratings[t2] = r2 + k * (s2 - (1.0 - e1))

    return model


def rankings_from_elo(model: EloModel) -> pd.DataFrame:
    rows = [
        {"team": team, "rating": rating}
        for team, rating in model.ratings.items()
    ]
    df = pd.DataFrame(rows).sort_values("rating", ascending=False)
    df["rank"] = np.arange(1, len(df) + 1)
    return df.reset_index(drop=True)
