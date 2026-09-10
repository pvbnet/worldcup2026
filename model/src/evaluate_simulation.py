from __future__ import annotations

import json
import math

import pandas as pd

from config import (
    ARTIFACTS_EVALUATION,
    ARTIFACTS_PREDICTIONS,
    CURRENT_YEAR,
    STAGE_COMPLETE,
    STAGE_GROUP,
    STAGE_LABELS,
    STAGE_ORDER,
    STAGE_PRE_TOURNAMENT,
    STAGE_QF,
    STAGE_R16,
    STAGE_R32,
    STAGE_SF,
    STRENGTH_SOURCES,
)
from teams import is_placeholder

SIM_EVENTS: list[str] = ["r32", "r16", "qf", "sf", "final", "win"]
SIM_EVENT_LABELS: dict[str, str] = {
    "r32": "Reach Round of 32",
    "r16": "Reach Round of 16",
    "qf": "Reach quarterfinals",
    "sf": "Reach semifinals",
    "final": "Reach final",
    "win": "Win tournament",
}

# Cumulative reach events from best finish to worst, used as the TRPS CDF.
_TRPS_CUMULATIVE: list[str] = ["win", "final", "sf", "qf", "r16", "r32"]
_P_KEY = {event: f"p_{event}" for event in SIM_EVENTS}
_Y_KEY = {event: f"y_{event}" for event in SIM_EVENTS}
_N_SLOTS = {"r32": 32, "r16": 16, "qf": 8, "sf": 4, "final": 2, "win": 1}
_QF_ONWARD_EVENTS: list[str] = ["qf", "sf", "final", "win"]
_EPS = 1e-15

# Events still random at each forecast vintage (locked rounds omitted).
UNRESOLVED_EVENTS: dict[str, list[str]] = {
    STAGE_PRE_TOURNAMENT: ["r32", "r16", "qf", "sf", "final", "win"],
    STAGE_GROUP: ["r16", "qf", "sf", "final", "win"],
    STAGE_R32: ["qf", "sf", "final", "win"],
    STAGE_R16: ["sf", "final", "win"],
    STAGE_QF: ["final", "win"],
    STAGE_SF: ["win"],
}

# Team is still alive at a vintage if they reached this already-resolved event.
_ALIVE_GATE: dict[str, str | None] = {
    STAGE_PRE_TOURNAMENT: None,
    STAGE_GROUP: "r32",
    STAGE_R32: "r16",
    STAGE_R16: "qf",
    STAGE_QF: "sf",
    STAGE_SF: "final",
}


def _wc2026(matches: pd.DataFrame) -> pd.DataFrame:
    year_matches = matches[matches["year"] == CURRENT_YEAR]
    if "competition" in year_matches.columns:
        year_matches = year_matches[year_matches["competition"] == "world_cup"]
    return year_matches


def _tournament_teams(wc: pd.DataFrame) -> list[str]:
    teams = pd.unique(pd.concat([wc["team1"], wc["team2"]], ignore_index=True))
    return sorted(str(team) for team in teams if not is_placeholder(str(team)))


def _team_groups(wc: pd.DataFrame) -> dict[str, str | None]:
    groups: dict[str, str | None] = {}
    grouped = wc[wc["group"].notna()]
    for row in grouped.itertuples(index=False):
        for team in (str(row.team1), str(row.team2)):
            if not is_placeholder(team):
                groups.setdefault(team, str(row.group))
    return groups


def realized_outcomes(matches: pd.DataFrame) -> dict[str, dict[str, int]]:
    """0/1 reach and win flags for every 2026 World Cup team."""
    wc = _wc2026(matches)
    teams = _tournament_teams(wc)
    flags = {team: {event: 0 for event in SIM_EVENTS} for team in teams}

    knockout = wc[wc["played"] & wc["stage"].isin(SIM_EVENTS[:-1])]
    for row in knockout.itertuples(index=False):
        stage = str(row.stage)
        for team in (str(row.team1), str(row.team2)):
            if team in flags:
                flags[team][stage] = 1

    finals = wc[wc["played"] & (wc["stage"] == "final")]
    for row in finals.itertuples(index=False):
        champion = row.advancer
        if champion is None or (isinstance(champion, float) and pd.isna(champion)):
            continue
        champion = str(champion)
        if champion in flags:
            flags[champion]["win"] = 1
            flags[champion]["final"] = 1
    return flags


def _clip01(value: float) -> float:
    return min(1.0, max(0.0, float(value)))


def _clip_log(value: float) -> float:
    return min(1.0 - _EPS, max(_EPS, float(value)))


def _binary_log_loss(prob: float, outcome: int) -> float:
    p = _clip_log(prob)
    return -(outcome * math.log(p) + (1 - outcome) * math.log(1 - p))


def _rank_masses(probs: dict[str, float]) -> list[float]:
    ordered = [_clip01(probs[event]) for event in _TRPS_CUMULATIVE]
    for i in range(1, len(ordered)):
        ordered[i] = max(ordered[i], ordered[i - 1])
    cumul = ordered + [1.0]
    prev = 0.0
    masses: list[float] = []
    for value in cumul:
        masses.append(max(value - prev, 0.0))
        prev = value
    total = sum(masses)
    if total <= 0:
        return [1.0 / len(masses)] * len(masses)
    return [mass / total for mass in masses]


def _team_trps(row: dict) -> float:
    """Ekstrøm et al. TRPS (eq. 2) for one team over the 7 partial ranks."""
    n_ranks_minus_1 = len(_TRPS_CUMULATIVE)
    masses = _rank_masses({event: row[_P_KEY[event]] for event in SIM_EVENTS})
    observed = [int(row[_Y_KEY[event]]) for event in _TRPS_CUMULATIVE]
    cdf_pred = 0.0
    team_sum = 0.0
    for idx in range(n_ranks_minus_1):
        cdf_pred += masses[idx]
        team_sum += (observed[idx] - cdf_pred) ** 2
    return team_sum / n_ranks_minus_1


def _trps(teams: list[dict]) -> float:
    """Mean over teams of `_team_trps`."""
    if not teams:
        return 0.0
    return sum(_team_trps(row) for row in teams) / len(teams)


def _baseline_trps_record(record: dict, stage: str) -> dict:
    unresolved = UNRESOLVED_EVENTS[stage]
    gate = _ALIVE_GATE[stage]
    alive = True if gate is None else bool(record[_Y_KEY[gate]])
    out = dict(record)
    for event in SIM_EVENTS:
        if event in unresolved:
            out[_P_KEY[event]] = _baseline_prob(stage, event, alive)
        else:
            out[_P_KEY[event]] = float(record[_Y_KEY[event]])
    return out


def _mean_brier_events(record: dict, events: list[str]) -> float:
    if not events:
        return 0.0
    return sum(
        (record[_P_KEY[event]] - record[_Y_KEY[event]]) ** 2 for event in events
    ) / len(events)


def _mean_log_loss_events(record: dict, events: list[str]) -> float:
    if not events:
        return 0.0
    return sum(
        _binary_log_loss(record[_P_KEY[event]], int(record[_Y_KEY[event]]))
        for event in events
    ) / len(events)


def _baseline_prob(stage: str, event: str, alive: bool) -> float:
    if not alive:
        return 0.0
    n_alive = _N_SLOTS.get(_ALIVE_GATE[stage] or "", 48)
    if _ALIVE_GATE[stage] is None:
        n_alive = 48
    return _N_SLOTS[event] / n_alive


def _score_artifact(
    payload: dict,
    outcomes: dict[str, dict[str, int]],
    groups: dict[str, str | None],
    stage: str,
) -> dict:
    unresolved = UNRESOLVED_EVENTS[stage]
    gate = _ALIVE_GATE[stage]
    rows_out: list[dict] = []
    event_sq: dict[str, list[float]] = {event: [] for event in unresolved}
    event_ll: dict[str, list[float]] = {event: [] for event in unresolved}
    event_base: dict[str, list[float]] = {event: [] for event in unresolved}
    event_ll_base: dict[str, list[float]] = {event: [] for event in unresolved}

    for team_row in payload.get("teams", []):
        team = str(team_row["team"])
        y = outcomes.get(team)
        if y is None:
            continue
        alive = True if gate is None else bool(y[gate])
        record: dict = {
            "team": team,
            "group": team_row.get("group") or groups.get(team),
        }
        for event in unresolved:
            p = _clip01(team_row.get(_P_KEY[event], 0.0))
            outcome = int(y[event])
            record[_P_KEY[event]] = p
            record[_Y_KEY[event]] = outcome
            event_sq[event].append((p - outcome) ** 2)
            event_ll[event].append(_binary_log_loss(p, outcome))
            baseline_p = _baseline_prob(stage, event, alive)
            event_base[event].append((baseline_p - outcome) ** 2)
            event_ll_base[event].append(_binary_log_loss(baseline_p, outcome))
        # Full p_/y_ needed for TRPS even when some events are locked.
        for event in SIM_EVENTS:
            record.setdefault(_P_KEY[event], _clip01(team_row.get(_P_KEY[event], 0.0)))
            record.setdefault(_Y_KEY[event], int(y[event]))
        qf_events = [event for event in _QF_ONWARD_EVENTS if event in unresolved]
        record["mean_brier"] = _mean_brier_events(record, unresolved)
        record["mean_brier_from_qf"] = _mean_brier_events(record, qf_events)
        record["mean_log_loss"] = _mean_log_loss_events(record, unresolved)
        record["mean_log_loss_from_qf"] = _mean_log_loss_events(record, qf_events)
        record["trps"] = _team_trps(record)
        rows_out.append(record)

    events_metrics: dict[str, dict] = {}
    event_briers: list[float] = []
    event_baselines: list[float] = []
    event_log_losses: list[float] = []
    event_ll_baselines: list[float] = []
    for event in unresolved:
        sq = event_sq[event]
        n = len(sq)
        brier = sum(sq) / n if n else 0.0
        logloss = sum(event_ll[event]) / n if n else 0.0
        baseline = sum(event_base[event]) / n if n else 0.0
        ll_baseline = sum(event_ll_base[event]) / n if n else 0.0
        events_metrics[event] = {
            "brier": brier,
            "log_loss": logloss,
            "n_teams": n,
        }
        event_briers.append(brier)
        event_baselines.append(baseline)
        event_log_losses.append(logloss)
        event_ll_baselines.append(ll_baseline)

    mean_brier = sum(event_briers) / len(event_briers) if event_briers else 0.0
    mean_baseline = (
        sum(event_baselines) / len(event_baselines) if event_baselines else 0.0
    )
    mean_log_loss = (
        sum(event_log_losses) / len(event_log_losses) if event_log_losses else 0.0
    )
    mean_log_loss_baseline = (
        sum(event_ll_baselines) / len(event_ll_baselines) if event_ll_baselines else 0.0
    )
    skill = None if mean_baseline <= 0 else 1.0 - mean_brier / mean_baseline
    log_loss_skill = (
        None
        if mean_log_loss_baseline <= 0
        else 1.0 - mean_log_loss / mean_log_loss_baseline
    )
    qf_events = [event for event in _QF_ONWARD_EVENTS if event in unresolved]
    qf_briers = [events_metrics[event]["brier"] for event in qf_events]
    qf_log_losses = [events_metrics[event]["log_loss"] for event in qf_events]
    qf_baselines = [
        sum(event_base[event]) / len(event_base[event])
        for event in qf_events
        if event_base[event]
    ]
    qf_ll_baselines = [
        sum(event_ll_base[event]) / len(event_ll_base[event])
        for event in qf_events
        if event_ll_base[event]
    ]
    mean_brier_from_qf = sum(qf_briers) / len(qf_briers) if qf_briers else 0.0
    mean_brier_baseline_from_qf = (
        sum(qf_baselines) / len(qf_baselines) if qf_baselines else 0.0
    )
    mean_log_loss_from_qf = (
        sum(qf_log_losses) / len(qf_log_losses) if qf_log_losses else 0.0
    )
    mean_log_loss_baseline_from_qf = (
        sum(qf_ll_baselines) / len(qf_ll_baselines) if qf_ll_baselines else 0.0
    )

    team_public = []
    for record in rows_out:
        public = {
            "team": record["team"],
            "group": record["group"],
            "mean_brier": record["mean_brier"],
            "mean_brier_from_qf": record["mean_brier_from_qf"],
            "mean_log_loss": record["mean_log_loss"],
            "mean_log_loss_from_qf": record["mean_log_loss_from_qf"],
            "trps": record["trps"],
        }
        for event in unresolved:
            public[_P_KEY[event]] = record[_P_KEY[event]]
            public[_Y_KEY[event]] = record[_Y_KEY[event]]
        team_public.append(public)

    return {
        "events": events_metrics,
        "trps": _trps(rows_out),
        "trps_baseline": _trps(
            [_baseline_trps_record(record, stage) for record in rows_out]
        ),
        "mean_brier": mean_brier,
        "mean_brier_baseline": mean_baseline,
        "mean_brier_from_qf": mean_brier_from_qf,
        "mean_brier_baseline_from_qf": mean_brier_baseline_from_qf,
        "brier_skill": skill,
        "mean_log_loss": mean_log_loss,
        "mean_log_loss_baseline": mean_log_loss_baseline,
        "mean_log_loss_from_qf": mean_log_loss_from_qf,
        "mean_log_loss_baseline_from_qf": mean_log_loss_baseline_from_qf,
        "log_loss_skill": log_loss_skill,
        "teams": team_public,
    }


def evaluate_simulations(matches: pd.DataFrame) -> dict:
    """Score committed 2026 Monte Carlo artifacts against realized outcomes."""
    outcomes = realized_outcomes(matches)
    groups = _team_groups(_wc2026(matches))
    stages_meta = [
        {
            "id": stage,
            "label": STAGE_LABELS[stage],
            "unresolved_events": list(UNRESOLVED_EVENTS[stage]),
        }
        for stage in STAGE_ORDER
        if stage != STAGE_COMPLETE
    ]
    payload = {
        "year": CURRENT_YEAR,
        "events": [{"id": event, "label": SIM_EVENT_LABELS[event]} for event in SIM_EVENTS],
        "stages": stages_meta,
        "strengths": {strength: {} for strength in STRENGTH_SOURCES},
    }

    for strength in STRENGTH_SOURCES:
        for stage in UNRESOLVED_EVENTS:
            path = ARTIFACTS_PREDICTIONS / f"worldcup_{stage}_{strength}.json"
            if not path.exists():
                continue
            artifact = json.loads(path.read_text(encoding="utf-8"))
            payload["strengths"][strength][stage] = _score_artifact(
                artifact, outcomes, groups, stage
            )

    tournament_mean_brier: dict = {
        "description": (
            "Pre-tournament mean Brier over reach events "
            "(equivalent to ACE Lab RPS: R32 through champion)"
        ),
        "stages": list(SIM_EVENTS),
        "qf_onward_stages": list(_QF_ONWARD_EVENTS),
    }
    for strength in STRENGTH_SOURCES:
        cell = payload["strengths"].get(strength, {}).get(STAGE_PRE_TOURNAMENT)
        if not cell:
            continue
        tournament_mean_brier[strength] = {
            "mean_brier": cell["mean_brier"],
            "mean_brier_baseline": cell["mean_brier_baseline"],
            "mean_brier_from_qf": cell["mean_brier_from_qf"],
            "mean_brier_baseline_from_qf": cell["mean_brier_baseline_from_qf"],
            "brier_skill": cell["brier_skill"],
            "n_teams": len(cell.get("teams", [])),
        }
    payload["tournament_mean_brier"] = tournament_mean_brier

    tournament_mean_log_loss: dict = {
        "description": (
            "Pre-tournament mean log-loss over reach events (R32 through champion)"
        ),
        "stages": list(SIM_EVENTS),
        "qf_onward_stages": list(_QF_ONWARD_EVENTS),
    }
    for strength in STRENGTH_SOURCES:
        cell = payload["strengths"].get(strength, {}).get(STAGE_PRE_TOURNAMENT)
        if not cell:
            continue
        tournament_mean_log_loss[strength] = {
            "mean_log_loss": cell["mean_log_loss"],
            "mean_log_loss_baseline": cell["mean_log_loss_baseline"],
            "mean_log_loss_from_qf": cell["mean_log_loss_from_qf"],
            "mean_log_loss_baseline_from_qf": cell["mean_log_loss_baseline_from_qf"],
            "log_loss_skill": cell["log_loss_skill"],
            "n_teams": len(cell.get("teams", [])),
        }
    payload["tournament_mean_log_loss"] = tournament_mean_log_loss

    out = ARTIFACTS_EVALUATION / "simulation_metrics.json"
    out.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return payload


def print_simulation_summary(payload: dict) -> None:
    print("Simulation evaluation (2026):")
    summary = payload.get("tournament_mean_brier", {})
    if summary:
        parts = []
        for strength in STRENGTH_SOURCES:
            cell = summary.get(strength)
            if not cell:
                parts.append(f"{strength}: missing")
                continue
            parts.append(
                f"{strength} brier={cell['mean_brier']:.4f} "
                f"from_qf={cell['mean_brier_from_qf']:.4f}"
            )
        print("  Pre-tournament mean Brier: " + " | ".join(parts))
    ll_summary = payload.get("tournament_mean_log_loss", {})
    if ll_summary:
        parts = []
        for strength in STRENGTH_SOURCES:
            cell = ll_summary.get(strength)
            if not cell:
                parts.append(f"{strength}: missing")
                continue
            parts.append(
                f"{strength} log_loss={cell['mean_log_loss']:.4f} "
                f"from_qf={cell['mean_log_loss_from_qf']:.4f}"
            )
        print("  Pre-tournament mean log-loss: " + " | ".join(parts))
    for stage_meta in payload.get("stages", []):
        stage = stage_meta["id"]
        parts: list[str] = []
        for strength in STRENGTH_SOURCES:
            cell = payload.get("strengths", {}).get(strength, {}).get(stage)
            if not cell:
                parts.append(f"{strength}: missing")
                continue
            parts.append(
                f"{strength} brier={cell['mean_brier']:.4f} "
                f"log_loss={cell['mean_log_loss']:.4f} trps={cell['trps']:.4f}"
            )
        print(f"  {stage}: " + " | ".join(parts))
