"""Unified real-bracket tournament simulator.

Used for every tournament-stage cutoff, including `pre_tournament`. Instead of
re-seeding survivors by rating (the old `tournament.py` shortcut), this module
reconstructs the *real* 2026 World Cup knockout bracket:

- Group standings (real, once played; simulated from scratch for
  `pre_tournament`) are resolved into concrete Round-of-32 fixtures using
  FIFA's published slot template + the "Annex C" best-third-place table
  (`model/data/wc2026_r32_bracket.json`).
- The Round of 16 -> Quarterfinal -> Semifinal -> Final feeder tree is derived
  once from the completed match data by chaining real participants forward
  round-by-round. Because bracket *slot* succession is fixed by the schedule
  (independent of who wins), this tree is valid for propagating simulated
  results too, not just the real ones.
- For a given stage cutoff, rounds at or before the cutoff are always taken
  from the real results (deterministic); rounds after the cutoff are
  Monte Carlo simulated using the active Elo/FIFA ratings.
"""

from __future__ import annotations

import json
import random
from collections import defaultdict
from collections.abc import Callable
from dataclasses import dataclass

import numpy as np
import pandas as pd

from config import (
    ARTIFACTS_PREDICTIONS,
    CURRENT_YEAR,
    DEFAULT_STRENGTH,
    KNOCKOUT_ROUND_ORDER,
    STAGE_INCLUDED_MATCH_STAGES,
    STAGE_PRE_TOURNAMENT,
    WC2026_BRACKET_DATA,
)
from models.elo import EloModel
from models.fifa import load_fifa_snapshot, ratings_for_strength
from teams import is_placeholder

ProgressCallback = Callable[[int, int], None]
Fixture = tuple[str, str]


def filter_training_matches(matches: pd.DataFrame, stage: str) -> pd.DataFrame:
    """Restrict training data to what would have been known as of `stage`.

    Non-2026-World-Cup rows (historical years, continental competitions,
    qualifiers) are always kept. Current-year World Cup rows are kept only if
    their per-match `stage` is already "known" at this cutoff.
    """
    is_current_wc = (matches["competition"] == "world_cup") & (
        matches["year"] == CURRENT_YEAR
    )
    included_stages = STAGE_INCLUDED_MATCH_STAGES.get(stage, set())
    keep_current_wc = matches["stage"].isin(included_stages)
    return matches[~is_current_wc | keep_current_wc].reset_index(drop=True)


# ---------------------------------------------------------------------------
# Group standings
# ---------------------------------------------------------------------------


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


def _standing_sort_key(s: TeamStanding):
    return (s.points, s.gd, s.gf, s.team)


def sort_standings(standings: list[TeamStanding]) -> list[TeamStanding]:
    """Same (points, gd, gf, team) tie-break already used elsewhere in the
    codebase (head-to-head, disciplinary points, and FIFA-ranking tiebreakers
    are not modeled)."""
    return sorted(standings, key=_standing_sort_key, reverse=True)


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


def _world_cup_year_matches(matches: pd.DataFrame, year: int) -> pd.DataFrame:
    year_matches = matches[matches["year"] == year]
    if "competition" in year_matches.columns:
        year_matches = year_matches[year_matches["competition"] == "world_cup"]
    return year_matches


def _group_letter(label: object) -> str:
    return str(label).replace("Group", "").strip()


def list_tournament_teams(matches: pd.DataFrame, year: int = CURRENT_YEAR) -> list[str]:
    year_matches = _world_cup_year_matches(matches, year)
    teams = pd.unique(
        pd.concat([year_matches["team1"], year_matches["team2"]], ignore_index=True)
    )
    return sorted(str(team) for team in teams if not is_placeholder(str(team)))


def precompute_group_fixtures(
    matches: pd.DataFrame, year: int = CURRENT_YEAR
) -> tuple[dict[str, list[Fixture]], dict[str, str], list[str]]:
    """Group fixtures keyed by bare letter (A-L), team -> full "Group X" label
    (for display), and the sorted 2026 team list."""
    year_matches = _world_cup_year_matches(matches, year)
    group_fixtures: dict[str, list[Fixture]] = {}
    team_group: dict[str, str] = {}

    group_rows = year_matches[year_matches["group"].notna()]
    for group_label in sorted(str(g) for g in group_rows["group"].unique()):
        letter = _group_letter(group_label)
        gm = group_rows[group_rows["group"] == group_label]
        fixtures: list[Fixture] = []
        for row in gm.itertuples(index=False):
            t1, t2 = str(row.team1), str(row.team2)
            if is_placeholder(t1) or is_placeholder(t2):
                continue
            fixtures.append((t1, t2))
            team_group.setdefault(t1, group_label)
            team_group.setdefault(t2, group_label)
        if fixtures:
            group_fixtures[letter] = fixtures

    teams = sorted(team_group.keys())
    return group_fixtures, team_group, teams


def real_group_standings(
    matches: pd.DataFrame, year: int = CURRENT_YEAR
) -> dict[str, list[TeamStanding]]:
    """Group standings computed from real, played group matches, keyed by
    bare group letter (A-L)."""
    year_matches = _world_cup_year_matches(matches, year)
    group_rows = year_matches[year_matches["group"].notna() & year_matches["played"]]
    tables: dict[str, dict[str, TeamStanding]] = defaultdict(dict)
    for row in group_rows.itertuples(index=False):
        letter = _group_letter(row.group)
        t1, t2 = str(row.team1), str(row.team2)
        if is_placeholder(t1) or is_placeholder(t2):
            continue
        g1, g2 = int(row.goals1), int(row.goals2)
        table = tables[letter]
        table.setdefault(t1, TeamStanding(team=t1))
        table.setdefault(t2, TeamStanding(team=t2))
        for team, gf, ga in ((t1, g1, g2), (t2, g2, g1)):
            st = table[team]
            st.played += 1
            st.gf += gf
            st.ga += ga
            if gf > ga:
                st.wins += 1
            elif gf < ga:
                st.losses += 1
            else:
                st.draws += 1
    return {letter: sort_standings(list(table.values())) for letter, table in tables.items()}


def simulate_group_standings(
    group_fixtures: dict[str, list[Fixture]],
    elo: EloModel,
    rng: random.Random,
) -> dict[str, list[TeamStanding]]:
    """Simulate every group from scratch for one Monte Carlo trial (ignores
    any real results), keyed by bare group letter."""
    result: dict[str, list[TeamStanding]] = {}
    for letter, fixtures in group_fixtures.items():
        tables: dict[str, TeamStanding] = {}
        for t1, t2 in fixtures:
            tables.setdefault(t1, TeamStanding(team=t1))
            tables.setdefault(t2, TeamStanding(team=t2))
        for t1, t2 in fixtures:
            probs = elo.match_probs(t1, t2)
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
        result[letter] = sort_standings(list(tables.values()))
    return result


# ---------------------------------------------------------------------------
# Round of 32 resolution (FIFA slot template + Annex C third-place table)
# ---------------------------------------------------------------------------

_BRACKET_DATA_CACHE: dict | None = None


def load_bracket_data() -> dict:
    global _BRACKET_DATA_CACHE
    if _BRACKET_DATA_CACHE is None:
        _BRACKET_DATA_CACHE = json.loads(
            WC2026_BRACKET_DATA.read_text(encoding="utf-8")
        )
    return _BRACKET_DATA_CACHE


def _position_team(pos: str, standings: dict[str, list[TeamStanding]]) -> str:
    """`pos` like '1E' (winner of group E), '2C' (runner-up of group C)."""
    rank = int(pos[0]) - 1
    letter = pos[1:]
    return standings[letter][rank].team


def _resolve_slot_side(
    side: dict, standings: dict[str, list[TeamStanding]], assignment: dict[str, str]
) -> str:
    if "pos" in side:
        return _position_team(side["pos"], standings)
    letter = assignment[side["third_place_slot"]]
    return standings[letter][2].team


def resolve_r32_fixtures(
    standings: dict[str, list[TeamStanding]], bracket_data: dict | None = None
) -> list[tuple[int, str, str]]:
    """Resolve the 16 real Round-of-32 fixtures from group standings (real or
    a single Monte Carlo trial's simulated standings), following FIFA's
    published slot template + Annex C table.

    Returns a list of (match_number, team1, team2).
    """
    bracket_data = bracket_data or load_bracket_data()

    thirds = [
        (letter, table[2]) for letter, table in standings.items() if len(table) >= 3
    ]
    ranked_thirds = sorted(thirds, key=lambda lt: _standing_sort_key(lt[1]), reverse=True)
    qualifying = sorted(letter for letter, _ in ranked_thirds[:8])
    key = ",".join(qualifying)
    combos = bracket_data["third_place_combinations"]
    if key not in combos:
        raise ValueError(f"No Annex C combination found for qualifying groups {qualifying}")
    assignment = combos[key]

    fixtures: list[tuple[int, str, str]] = []
    for entry in bracket_data["slot_template"]:
        team1 = _resolve_slot_side(entry["team1"], standings, assignment)
        team2 = _resolve_slot_side(entry["team2"], standings, assignment)
        fixtures.append((entry["match"], team1, team2))
    return fixtures


# ---------------------------------------------------------------------------
# Real bracket tree (R32 -> R16 -> QF -> SF -> Final feeder links)
# ---------------------------------------------------------------------------


@dataclass
class BracketTree:
    rounds: dict[str, list[str]]  # round name -> ordered list of slot ids
    feeders: dict[str, tuple[str, str]]  # slot id -> (feeder slot a, feeder slot b)
    real_teams: dict[str, Fixture]  # slot id -> real (team1, team2)
    real_winner: dict[str, str]  # slot id -> real advancer


def _stage_rows(matches: pd.DataFrame, stage: str, year: int) -> pd.DataFrame:
    year_matches = _world_cup_year_matches(matches, year)
    return year_matches[year_matches["stage"] == stage]


def _find_feeder_slot(
    team: str, prev_round: str, real_teams: dict[str, Fixture], rounds: dict[str, list[str]]
) -> str:
    for slot_id in rounds[prev_round]:
        if team in real_teams[slot_id]:
            return slot_id
    raise ValueError(f"Could not find a {prev_round} slot containing {team!r}")


def build_bracket_tree(matches: pd.DataFrame, year: int = CURRENT_YEAR) -> BracketTree:
    """Derive the real 2026 knockout bracket tree (slot ids + feeder links)
    from the completed match data. Also validates that resolving the real
    group standings through the Annex C table reproduces the real Round of
    32 exactly (raises if not, e.g. if the bracket data is stale)."""
    standings = real_group_standings(matches, year)
    r32_resolved = resolve_r32_fixtures(standings)
    resolved_by_pair = {frozenset((t1, t2)): match_no for match_no, t1, t2 in r32_resolved}

    real_teams: dict[str, Fixture] = {}
    real_winner: dict[str, str] = {}
    rounds: dict[str, list[str]] = {name: [] for name in KNOCKOUT_ROUND_ORDER}
    feeders: dict[str, tuple[str, str]] = {}

    r32_rows = list(_stage_rows(matches, "r32", year).itertuples(index=False))
    if len(r32_rows) != 16:
        raise ValueError(f"Expected 16 real Round of 32 matches, found {len(r32_rows)}")

    for row in r32_rows:
        t1, t2 = str(row.team1), str(row.team2)
        match_no = resolved_by_pair.get(frozenset((t1, t2)))
        if match_no is None:
            raise ValueError(
                f"Real Round of 32 match {t1} vs {t2} does not match any fixture "
                "resolved from the Annex C table; wc2026_r32_bracket.json may be "
                "stale, or the group tie-break diverges from the real result."
            )
        slot_id = f"r32_{match_no}"
        real_teams[slot_id] = (t1, t2)
        real_winner[slot_id] = str(row.advancer)
        rounds["r32"].append(slot_id)

    prev_round = "r32"
    for round_name in KNOCKOUT_ROUND_ORDER[1:]:
        rows = list(_stage_rows(matches, round_name, year).itertuples(index=False))
        for i, row in enumerate(rows):
            t1, t2 = str(row.team1), str(row.team2)
            slot_id = f"{round_name}_{i}"
            feeders[slot_id] = (
                _find_feeder_slot(t1, prev_round, real_teams, rounds),
                _find_feeder_slot(t2, prev_round, real_teams, rounds),
            )
            real_teams[slot_id] = (t1, t2)
            real_winner[slot_id] = str(row.advancer)
            rounds[round_name].append(slot_id)
        prev_round = round_name

    if len(rounds["final"]) != 1:
        raise ValueError(f"Expected exactly 1 real Final match, found {len(rounds['final'])}")

    return BracketTree(rounds=rounds, feeders=feeders, real_teams=real_teams, real_winner=real_winner)


# ---------------------------------------------------------------------------
# Unified simulator
# ---------------------------------------------------------------------------


class RealBracketSimulator:
    """Simulates the real 2026 World Cup format for any stage cutoff,
    including `pre_tournament` (full simulation of groups + the real
    Round-of-32 draw via Annex C)."""

    def __init__(
        self,
        matches: pd.DataFrame,
        pure_elo: EloModel,
        strength: str = DEFAULT_STRENGTH,
        stage: str = STAGE_PRE_TOURNAMENT,
        year: int = CURRENT_YEAR,
    ):
        self.matches = matches
        self.pure_elo = pure_elo
        self.strength = strength if strength in ("elo", "fifa") else DEFAULT_STRENGTH
        self.stage = stage
        self.year = year

        fifa = load_fifa_snapshot()
        (
            self._group_fixtures,
            self._team_group,
            self._teams,
        ) = precompute_group_fixtures(matches, year)
        self.elo = ratings_for_strength(
            self.pure_elo, fifa, self.strength, teams=self._teams
        )
        self._tree = build_bracket_tree(matches, year)

        included = STAGE_INCLUDED_MATCH_STAGES.get(stage, set())
        self._simulated_rounds = [r for r in KNOCKOUT_ROUND_ORDER if r not in included]
        self._entry_round = self._simulated_rounds[0] if self._simulated_rounds else None
        self._simulate_group = stage == STAGE_PRE_TOURNAMENT
        self._bracket_data = load_bracket_data() if self._simulate_group else None

    def _run_trial(
        self, rng: random.Random
    ) -> tuple[dict[str, Fixture], dict[str, str]]:
        tree = self._tree
        winner: dict[str, str] = {}
        teams: dict[str, Fixture] = {}

        if self._simulate_group:
            standings = simulate_group_standings(self._group_fixtures, self.elo, rng)
            resolved = resolve_r32_fixtures(standings, self._bracket_data)
            for match_no, t1, t2 in resolved:
                teams[f"r32_{match_no}"] = (t1, t2)

        for round_name in KNOCKOUT_ROUND_ORDER:
            simulate_this_round = round_name in self._simulated_rounds
            for slot_id in tree.rounds[round_name]:
                if slot_id in teams:
                    t1, t2 = teams[slot_id]
                elif simulate_this_round and round_name != self._entry_round:
                    fa, fb = tree.feeders[slot_id]
                    t1, t2 = winner[fa], winner[fb]
                else:
                    # Fixed round, or the entry round (participants are known
                    # in advance: either the real fixture, or already
                    # supplied above via the simulated Round of 32).
                    t1, t2 = tree.real_teams[slot_id]
                teams[slot_id] = (t1, t2)

                if simulate_this_round:
                    probs = self.elo.match_probs(t1, t2)
                    winner[slot_id] = resolve_knockout(t1, t2, probs, rng, self.elo)
                else:
                    winner[slot_id] = tree.real_winner[slot_id]

        return teams, winner

    def run(
        self,
        simulations: int = 1000,
        seed: int = 42,
        on_progress: ProgressCallback | None = None,
        progress_every: int = 100,
    ) -> pd.DataFrame:
        tree = self._tree
        reach_counts: dict[str, dict[str, int]] = {
            round_name: defaultdict(int) for round_name in KNOCKOUT_ROUND_ORDER
        }
        win_counts: dict[str, int] = defaultdict(int)

        # Nothing is random when every round is fixed (stage == "complete");
        # a single deterministic pass is enough.
        trials = simulations if self._entry_round is not None else 1
        trials = max(trials, 1)

        rng = random.Random(seed)
        for i in range(trials):
            slot_teams, winner = self._run_trial(rng)
            for round_name in KNOCKOUT_ROUND_ORDER:
                for slot_id in tree.rounds[round_name]:
                    t1, t2 = slot_teams[slot_id]
                    reach_counts[round_name][t1] += 1
                    reach_counts[round_name][t2] += 1
            champion = winner[tree.rounds["final"][0]]
            win_counts[champion] += 1

            done = i + 1
            if on_progress and self._entry_round is not None and (
                done % progress_every == 0 or done == trials
            ):
                on_progress(done, trials)

        rows = []
        for team in self._teams:
            rows.append(
                {
                    "team": team,
                    "p_r32": reach_counts["r32"][team] / trials,
                    "p_r16": reach_counts["r16"][team] / trials,
                    "p_qf": reach_counts["qf"][team] / trials,
                    "p_sf": reach_counts["sf"][team] / trials,
                    "p_final": reach_counts["final"][team] / trials,
                    "p_win": win_counts[team] / trials,
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

    def save_predictions(self, df: pd.DataFrame, simulations: int | None = None) -> None:
        out = ARTIFACTS_PREDICTIONS / f"worldcup_{self.stage}_{self.strength}.json"
        effective_sims = simulations if simulations is not None else 0
        if self._entry_round is None:
            effective_sims = 0
        payload = {
            "strength": self.strength,
            "stage": self.stage,
            "simulations": effective_sims,
            "n_teams": len(df),
            "teams": df.to_dict(orient="records"),
        }
        out.write_text(json.dumps(payload, indent=2), encoding="utf-8")
