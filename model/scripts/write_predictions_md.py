#!/usr/bin/env python3
"""Write docs/predictions.md from committed pre-tournament prediction JSON."""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from config import ARTIFACTS_PREDICTIONS, ARTIFACTS_TRAINING, PROJECT_ROOT
from models.elo import EloModel
from models.fifa import load_fifa_snapshot, rank_lookup, rank_table_from_values

OUT_PATH = PROJECT_ROOT / "docs" / "predictions.md"
DASHBOARD_URL = "https://worldcup2026-dashboard.web.app/"


def _pct(value: float) -> str:
    return f"{value * 100:.1f}%"


def _load_predictions(strength: str) -> dict:
    path = ARTIFACTS_PREDICTIONS / f"worldcup_pre_tournament_{strength}.json"
    return json.loads(path.read_text(encoding="utf-8"))


def _table(payload: dict, elo: EloModel, fifa) -> str:
    teams = [row["team"] for row in payload.get("teams", [])]
    elo_ranks = rank_table_from_values(
        {team: elo.ratings.get(team, 1500.0) for team in teams}
    )
    rows = sorted(payload.get("teams", []), key=lambda r: int(r.get("rank", 999)))
    lines = [
        "| Sim Rank | Elo Rank | FIFA Rank | Team | Elo | P(R32) | P(R16) | P(QF) | P(SF) | P(Final) | P(Win WC) |",
        "| ---: | ---: | ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for row in rows:
        team = row["team"]
        lines.append(
            "| {sim} | {elo_rank} | {fifa_rank} | {team} | {elo} | {p_r32} | {p_r16} | {p_qf} | {p_sf} | {p_final} | {p_win} |".format(
                sim=int(row.get("rank", 0)),
                elo_rank=elo_ranks.get(team, 999),
                fifa_rank=rank_lookup(fifa, team),
                team=team,
                elo=round(float(row.get("rating", 1500.0))),
                p_r32=_pct(float(row.get("p_r32", 0.0))),
                p_r16=_pct(float(row.get("p_r16", 0.0))),
                p_qf=_pct(float(row.get("p_qf", 0.0))),
                p_sf=_pct(float(row.get("p_sf", 0.0))),
                p_final=_pct(float(row.get("p_final", 0.0))),
                p_win=_pct(float(row.get("p_win", 0.0))),
            )
        )
    return "\n".join(lines)


def write_predictions_md() -> Path:
    elo_payload = _load_predictions("elo")
    fifa_payload = _load_predictions("fifa")
    elo = EloModel.load(ARTIFACTS_TRAINING / "elo_pre_tournament.json")
    fifa = load_fifa_snapshot()
    n_sims = int(elo_payload.get("simulations") or fifa_payload.get("simulations") or 0)

    body = f"""# Pre-tournament predictions

Monte Carlo stage-reach and win probabilities **before any 2026 match**. 

Same table as the Predictions page in the live dashboard app at: [{DASHBOARD_URL}]({DASHBOARD_URL}). 

Generated from committed `worldcup_pre_tournament_{{elo,fifa}}.json` ({n_sims:,} runs). Regenerate with `python scripts/write_predictions_md.py` from `model/`.

## Elo ratings

{_table(elo_payload, elo, fifa)}

## FIFA rankings

{_table(fifa_payload, elo, fifa)}
"""
    OUT_PATH.write_text(body, encoding="utf-8")
    return OUT_PATH


def main() -> None:
    path = write_predictions_md()
    print(f"Wrote {path}")


if __name__ == "__main__":
    main()
