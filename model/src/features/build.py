from __future__ import annotations

import numpy as np
import pandas as pd

KNOCKOUT_STAGES = {"final", "sf", "qf", "r16", "r32", "third", "knockout"}


def _result_points(goals1: int, goals2: int) -> tuple[int, int]:
    if goals1 > goals2:
        return 3, 0
    if goals1 < goals2:
        return 0, 3
    return 1, 1


def build_training_frame(matches: pd.DataFrame) -> pd.DataFrame:
    played = matches[matches["played"]].copy()
    played = played.sort_values(["date", "year"]).reset_index(drop=True)

    rows: list[dict] = []
    team_history: dict[str, list[dict]] = {}
    team_last_date: dict[str, pd.Timestamp] = {}

    for _, row in played.iterrows():
        t1, t2 = row["team1"], row["team2"]
        g1, g2 = int(row["goals1"]), int(row["goals2"])
        p1, p2 = _result_points(g1, g2)
        date = pd.to_datetime(row["date"])
        competition = row["competition"] if "competition" in row else "world_cup"
        weight = float(row["weight"]) if "weight" in row and pd.notna(row["weight"]) else 1.0

        h1 = team_history.get(t1, [])
        h2 = team_history.get(t2, [])

        form1 = np.mean([m["gd"] for m in h1[-5:]]) if h1 else 0.0
        form2 = np.mean([m["gd"] for m in h2[-5:]]) if h2 else 0.0
        pts1 = np.mean([m["pts"] for m in h1[-5:]]) if h1 else 0.0
        pts2 = np.mean([m["pts"] for m in h2[-5:]]) if h2 else 0.0

        days1 = (date - team_last_date[t1]).days if t1 in team_last_date else 7
        days2 = (date - team_last_date[t2]).days if t2 in team_last_date else 7

        if g1 > g2:
            outcome = 0
        elif g1 < g2:
            outcome = 2
        else:
            outcome = 1

        rows.append(
            {
                "match_id": row["match_id"],
                "year": row["year"],
                "date": row["date"],
                "stage": row["stage"],
                "competition": competition,
                "weight": weight,
                "team1": t1,
                "team2": t2,
                "goals1": g1,
                "goals2": g2,
                "outcome": outcome,
                "form1": form1,
                "form2": form2,
                "pts1": pts1,
                "pts2": pts2,
                "days1": days1,
                "days2": days2,
                "form_diff": form1 - form2,
                "pts_diff": pts1 - pts2,
                "days_diff": days1 - days2,
                "is_knockout": int(row["stage"] in KNOCKOUT_STAGES),
            }
        )

        team_history.setdefault(t1, []).append({"gd": g1 - g2, "pts": p1})
        team_history.setdefault(t2, []).append({"gd": g2 - g1, "pts": p2})
        team_last_date[t1] = date
        team_last_date[t2] = date

    return pd.DataFrame(rows)
