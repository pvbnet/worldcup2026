from __future__ import annotations

import json
import random
from collections import defaultdict
from collections.abc import Callable
from dataclasses import dataclass

import numpy as np
import pandas as pd

from config import ARTIFACTS_PREDICTIONS, CURRENT_YEAR, DEFAULT_STRENGTH
from models.elo import EloModel
from models.fifa import load_fifa_snapshot, ratings_for_strength
from teams import is_placeholder

STAGE_GROUP = 1
STAGE_R32 = 2  # advanced from groups (knockout path; stand-in for R32)
STAGE_R16 = 3
STAGE_QF = 4
STAGE_SF = 5
STAGE_FINAL = 6
STAGE_CHAMPION = 7

ProgressCallback = Callable[[int, int], None]
# (team1, team2)
Fixture = tuple[str, str]


def _world_cup_year_matches(matches: pd.DataFrame, year: int) -> pd.DataFrame:
    year_matches = matches[matches["year"] == year]
    if "competition" in year_matches.columns:
        year_matches = year_matches[year_matches["competition"] == "world_cup"]
    return year_matches


def _2026_teams(matches: pd.DataFrame) -> list[str]:
    year_matches = _world_cup_year_matches(matches, CURRENT_YEAR)
    teams = pd.unique(
        pd.concat([year_matches["team1"], year_matches["team2"]], ignore_index=True)
    )
    return sorted(str(team) for team in teams if not is_placeholder(str(team)))


def _precompute_group_fixtures(
    matches: pd.DataFrame,
) -> tuple[dict[str, list[Fixture]], dict[str, str | None], list[str]]:
    """Build WC group fixtures, team→group map, and team list once."""
    year_matches = _world_cup_year_matches(matches, CURRENT_YEAR)
    group_fixtures: dict[str, list[Fixture]] = {}
    team_group: dict[str, str | None] = {}

    group_rows = year_matches[year_matches["group"].notna()]
    for group in sorted(str(g) for g in group_rows["group"].unique()):
        gm = group_rows[group_rows["group"] == group]
        fixtures: list[Fixture] = []
        for row in gm.itertuples(index=False):
            t1, t2 = str(row.team1), str(row.team2)
            if is_placeholder(t1) or is_placeholder(t2):
                continue
            fixtures.append((t1, t2))
            team_group.setdefault(t1, group)
            team_group.setdefault(t2, group)
        if fixtures:
            group_fixtures[group] = fixtures

    teams = sorted(team_group.keys())
    return group_fixtures, team_group, teams


@dataclass
class TeamStanding:
    team: str
    played: int = 0
    wins: int = 0
    draws: int = 0
    losses: int = 0
    gf: int = 0
    ga: int = 0

    @property
    def points(self) -> int:
        return self.wins * 3 + self.draws

    @property
    def gd(self) -> int:
        return self.gf - self.ga


def sample_score(probs: dict[str, float], rng: random.Random) -> tuple[int, int]:
    roll = rng.random()
    if roll < probs["team1"]:
        return 1, 0
    if roll < probs["team1"] + probs["draw"]:
        return 1, 1
    return 0, 1


def resolve_knockout(
    team1: str,
    team2: str,
    probs: dict[str, float],
    rng: random.Random,
    elo: EloModel,
) -> str:
    g1, g2 = sample_score(probs, rng)
    if g1 > g2:
        return team1
    if g2 > g1:
        return team2
    r1 = elo.ratings.get(team1, 1500.0)
    r2 = elo.ratings.get(team2, 1500.0)
    p1 = 1.0 / (1.0 + 10 ** ((r2 - r1) / 400.0))
    return team1 if rng.random() < p1 else team2


class TournamentSimulator:
    def __init__(
        self,
        matches: pd.DataFrame,
        pure_elo: EloModel,
        strength: str = DEFAULT_STRENGTH,
    ):
        self.matches = matches
        self.pure_elo = pure_elo
        self.strength = strength if strength in ("elo", "fifa") else DEFAULT_STRENGTH
        fifa = load_fifa_snapshot()
        (
            self._group_fixtures,
            self._team_group,
            self._teams,
        ) = _precompute_group_fixtures(matches)
        self.elo = ratings_for_strength(
            self.pure_elo, fifa, self.strength, teams=self._teams
        )
        self._prob_cache: dict[tuple[str, str, str], dict[str, float]] = {}

    def predict_probs(
        self, team1: str, team2: str, stage: str = "group"
    ) -> dict[str, float]:
        cache_key = (team1, team2, stage)
        if cache_key in self._prob_cache:
            return self._prob_cache[cache_key]
        result = self.elo.match_probs(team1, team2)
        self._prob_cache[cache_key] = result
        return result

    def group_standings_from_fixtures(
        self, fixtures: list[Fixture], rng: random.Random
    ) -> list[TeamStanding]:
        """Simulate a group from scratch (always sample; ignore played scores)."""
        tables: dict[str, TeamStanding] = {}
        for t1, t2 in fixtures:
            tables.setdefault(t1, TeamStanding(team=t1))
            tables.setdefault(t2, TeamStanding(team=t2))

        for t1, t2 in fixtures:
            probs = self.predict_probs(t1, t2, stage="group")
            g1, g2 = sample_score(probs, rng)
            for team, gf, ga, opp_gf in (
                (t1, g1, g2, g2),
                (t2, g2, g1, g1),
            ):
                st = tables[team]
                st.played += 1
                st.gf += gf
                st.ga += ga
                if gf > opp_gf:
                    st.wins += 1
                elif gf < opp_gf:
                    st.losses += 1
                else:
                    st.draws += 1

        return sorted(
            tables.values(),
            key=lambda s: (s.points, s.gd, s.gf, s.team),
            reverse=True,
        )

    def simulate_once(self, rng: random.Random) -> dict[str, object]:
        group_winners: dict[str, list[str]] = {}

        for group, fixtures in self._group_fixtures.items():
            standings = self.group_standings_from_fixtures(fixtures, rng)
            group_winners[group] = [s.team for s in standings[:2]]

        stage_reached: dict[str, int] = defaultdict(int)
        finalists: set[str] = set()

        for team_list in group_winners.values():
            for team in team_list:
                # Group advancers enter the knockout path (R32 stand-in).
                stage_reached[team] = max(stage_reached[team], STAGE_R32)

        remaining_teams = {t for pair in group_winners.values() for t in pair}
        ranked = sorted(
            remaining_teams,
            key=lambda t: self.elo.ratings.get(t, 1500.0),
            reverse=True,
        )
        bracket = ranked[:16] if len(ranked) >= 16 else ranked

        # Teams placed in the 16-team bracket have reached the Round of 16.
        for team in bracket:
            stage_reached[team] = max(stage_reached[team], STAGE_R16)

        # Winning a round marks reaching the *next* stage.
        stage_for_round = {
            16: STAGE_QF,
            8: STAGE_SF,
            4: STAGE_FINAL,
        }

        while len(bracket) > 1:
            if len(bracket) == 2:
                for team in bracket:
                    stage_reached[team] = max(stage_reached[team], STAGE_FINAL)
                finalists = set(bracket)

            next_round: list[str] = []
            for i in range(0, len(bracket), 2):
                if i + 1 >= len(bracket):
                    next_round.append(bracket[i])
                    continue
                t1, t2 = bracket[i], bracket[i + 1]
                probs = self.predict_probs(t1, t2, stage="knockout")
                winner = resolve_knockout(t1, t2, probs, rng, self.elo)
                next_round.append(winner)
                if len(bracket) in stage_for_round:
                    stage = stage_for_round[len(bracket)]
                    stage_reached[winner] = max(stage_reached[winner], stage)
            bracket = next_round

        champion = bracket[0]
        stage_reached[champion] = STAGE_CHAMPION
        finalists.add(champion)

        return {
            "champion": champion,
            "finalists": finalists,
            "stage_reached": dict(stage_reached),
        }

    def run(
        self,
        simulations: int = 1000,
        seed: int = 42,
        on_progress: ProgressCallback | None = None,
        progress_every: int = 100,
    ) -> pd.DataFrame:
        self._prob_cache.clear()
        rng = random.Random(seed)
        win_counts: dict[str, int] = defaultdict(int)
        r32_counts: dict[str, int] = defaultdict(int)
        r16_counts: dict[str, int] = defaultdict(int)
        qf_counts: dict[str, int] = defaultdict(int)
        sf_counts: dict[str, int] = defaultdict(int)
        final_counts: dict[str, int] = defaultdict(int)
        teams = self._teams

        for i in range(simulations):
            result = self.simulate_once(rng)
            champion = str(result["champion"])
            win_counts[champion] += 1
            stage_reached = result["stage_reached"]
            assert isinstance(stage_reached, dict)
            for team, stage in stage_reached.items():
                team = str(team)
                stage_i = int(stage)
                if stage_i >= STAGE_R32:
                    r32_counts[team] += 1
                if stage_i >= STAGE_R16:
                    r16_counts[team] += 1
                if stage_i >= STAGE_QF:
                    qf_counts[team] += 1
                if stage_i >= STAGE_SF:
                    sf_counts[team] += 1
                if stage_i >= STAGE_FINAL:
                    final_counts[team] += 1
            done = i + 1
            if on_progress and (done % progress_every == 0 or done == simulations):
                on_progress(done, simulations)

        rows = []
        for team in teams:
            rows.append(
                {
                    "team": team,
                    "p_r32": r32_counts[team] / simulations,
                    "p_r16": r16_counts[team] / simulations,
                    "p_qf": qf_counts[team] / simulations,
                    "p_sf": sf_counts[team] / simulations,
                    "p_final": final_counts[team] / simulations,
                    "p_win": win_counts[team] / simulations,
                    "rating": self.pure_elo.ratings.get(team, 1500.0),
                    "active_rating": self.elo.ratings.get(team, 1500.0),
                    "group": self._team_group.get(team),
                }
            )

        df = pd.DataFrame(rows).sort_values(
            ["p_win", "rating"], ascending=[False, False]
        )
        mono_cols = ["p_win", "p_final", "p_sf", "p_qf", "p_r16", "p_r32"]
        for left, right in zip(mono_cols, mono_cols[1:]):
            if (df[left] > df[right] + 1e-9).any():
                bad = df[df[left] > df[right]][["team", left, right]]
                raise RuntimeError(
                    f"{left} must be <= {right}; violations:\n{bad}"
                )
        df["rank"] = np.arange(1, len(df) + 1)
        return df.reset_index(drop=True)

    def save_predictions(
        self, df: pd.DataFrame, strength: str, simulations: int | None = None
    ) -> None:
        out = ARTIFACTS_PREDICTIONS / f"worldcup_{strength}.json"
        payload = {
            "strength": strength,
            "simulations": simulations if simulations is not None else 0,
            "n_teams": len(df),
            "teams": df.to_dict(orient="records"),
        }
        out.write_text(json.dumps(payload, indent=2), encoding="utf-8")
