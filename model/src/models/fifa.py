from __future__ import annotations

import json
import math
from dataclasses import dataclass

from config import MODEL_ROOT
from models.elo import EloModel
from teams import canonicalize

FIFA_DATA_PATH = MODEL_ROOT / "data" / "fifa_rankings.json"
DEFAULT_FIFA_RANK = 100
PSEUDO_ELO_BASE = 2100.0
PSEUDO_ELO_SCALE = 25.0

# Separate calibration used only for *seeding* fit_elo's initial ratings.
# Unlike PSEUDO_ELO_BASE/SCALE above (which produce a ~1900-2100 scale used
# for a standalone FIFA-only comparison model in evaluate.py), these constants
# are tuned to land on the same numeric scale as our *trained* Elo ratings
# (observed to span roughly 1330-1720, median ~1480 across a full training
# run). Rank 1 seeds near the top of that range, and the bottom of the FIFA
# ranking (~rank 210) seeds near the bottom of it.
SEED_RATING_BASE = 1720.0
SEED_RATING_SCALE = 48.0


@dataclass
class FifaSnapshot:
    snapshot_id: str
    description: str
    ranks: dict[str, int]


def load_fifa_data() -> dict:
    return json.loads(FIFA_DATA_PATH.read_text(encoding="utf-8"))


def load_fifa_snapshot(snapshot_id: str | None = None) -> FifaSnapshot:
    payload = load_fifa_data()
    snapshot_id = snapshot_id or payload["display_snapshot"]
    snap = payload["snapshots"][snapshot_id]
    ranks = {canonicalize(team): int(rank) for team, rank in snap["teams"].items()}
    return FifaSnapshot(
        snapshot_id=snapshot_id,
        description=snap.get("description", snapshot_id),
        ranks=ranks,
    )


def pseudo_elo_from_rank(rank: int) -> float:
    rank = max(int(rank), 1)
    return PSEUDO_ELO_BASE - PSEUDO_ELO_SCALE * math.log2(rank)


def seed_rating_from_rank(rank: int) -> float:
    """Map a FIFA rank to a starting Elo rating on the trained-Elo scale.

    Used to seed fit_elo so teams enter the training window already spread
    out by real pre-existing strength, instead of a flat 1500 for everyone.
    """
    rank = max(int(rank), 1)
    return SEED_RATING_BASE - SEED_RATING_SCALE * math.log2(rank)


def seed_ratings_from_fifa(
    teams: list[str], snapshot_id: str | None = None
) -> dict[str, float]:
    """Build a {team: seed_rating} map from a FIFA snapshot for fit_elo.

    Defaults to the data file's "tuning_snapshot" (a pre-training-window
    ranking, so the seed doesn't leak knowledge of results already inside
    the training data). Teams absent from the snapshot fall back to
    DEFAULT_FIFA_RANK.
    """
    payload = load_fifa_data()
    snapshot_id = snapshot_id or payload.get("tuning_snapshot") or payload["display_snapshot"]
    snap = load_fifa_snapshot(snapshot_id)
    return {
        team: seed_rating_from_rank(snap.ranks.get(canonicalize(team), DEFAULT_FIFA_RANK))
        for team in teams
    }


def ratings_for_strength(
    elo: EloModel,
    fifa: FifaSnapshot,
    strength: str,
    teams: list[str] | None = None,
) -> EloModel:
    """Return an EloModel whose ratings come from trained Elo or FIFA ranks."""
    strength = strength if strength in ("elo", "fifa") else "elo"
    teams = teams or list(elo.ratings.keys())
    ratings: dict[str, float] = {}
    for team in teams:
        team = canonicalize(team)
        if strength == "fifa":
            fifa_rank = fifa.ranks.get(team, DEFAULT_FIFA_RANK)
            ratings[team] = pseudo_elo_from_rank(fifa_rank)
        else:
            ratings[team] = elo.ratings.get(team, 1500.0)
    return EloModel(
        ratings=ratings,
        k_factor=elo.k_factor,
        home_advantage=elo.home_advantage,
    )


def rank_lookup(fifa: FifaSnapshot, team: str) -> int:
    return fifa.ranks.get(canonicalize(team), DEFAULT_FIFA_RANK)


def rank_table_from_values(values: dict[str, float]) -> dict[str, int]:
    ordered = sorted(values.items(), key=lambda item: (-item[1], item[0]))
    return {team: idx + 1 for idx, (team, _) in enumerate(ordered)}
