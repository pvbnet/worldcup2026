#!/usr/bin/env python3
"""Write docs/evaluation-results.md from committed evaluation JSON."""

from __future__ import annotations

import json
import math
import sys
from pathlib import Path
from xml.sax.saxutils import escape

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from config import ARTIFACTS_EVALUATION, ARTIFACTS_TRAINING, PROJECT_ROOT

DASHBOARD_URL = "https://worldcup2026-dashboard.web.app/"
ACE_URL = "https://ac3lab.github.io/blog/2026/model_comparison_en/"
MD_PATH = PROJECT_ROOT / "docs" / "evaluation-results.md"
SVG_PATH = PROJECT_ROOT / "docs" / "evaluation-headline.svg"
TEAM_SVG_PATH = PROJECT_ROOT / "docs" / "evaluation-elo-teams.svg"
EVENTS = ["r32", "r16", "qf", "sf", "final", "win"]
EVENT_LABELS = {
    "r32": "R32",
    "r16": "R16",
    "qf": "QF",
    "sf": "SF",
    "final": "Final",
    "win": "Win",
}
HEADLINE_COLS = [
    *EVENTS,
    "rps",
    "rps_qf",
    "log_loss",
    "log_loss_qf",
]
HEADLINE_HEADERS = [
    *(EVENT_LABELS[e] for e in EVENTS),
    "RPS",
    "RPS QF→",
    "Log-loss",
    "Log-loss QF→",
]
MD_HEADLINE_HEADERS = [
    *(f"Brier {EVENT_LABELS[e]}" for e in EVENTS),
    "RPS (avg Brier)",
    "RPS QF→",
    "Log-loss",
    "Log-loss QF→",
]
N_STAGE_COLS = len(EVENTS)
# Pre-tournament equal-share: remaining slots split uniformly over 48 teams.
_BASELINE_SLOTS = {"r32": 32, "r16": 16, "qf": 8, "sf": 4, "final": 2, "win": 1}
_BASELINE_N_TEAMS = 48
_EPS = 1e-15


def _load(name: str) -> dict:
    return json.loads((ARTIFACTS_EVALUATION / name).read_text(encoding="utf-8"))


def _fmt(value: float | None, digits: int = 4) -> str:
    if value is None:
        return "—"
    return f"{value:.{digits}f}"


def _baseline_event_scores() -> dict[str, dict[str, float]]:
    scores: dict[str, dict[str, float]] = {}
    for event, slots in _BASELINE_SLOTS.items():
        p = slots / _BASELINE_N_TEAMS
        p_clip = min(max(p, _EPS), 1.0 - _EPS)
        scores[event] = {
            "brier": p * (1.0 - p),
            "log_loss": -(p * math.log(p_clip) + (1.0 - p) * math.log(1.0 - p_clip)),
        }
    return scores


def _baseline_headline_row(sim: dict) -> dict:
    means_b = sim["tournament_mean_brier"]["elo"]
    means_ll = sim["tournament_mean_log_loss"]["elo"]
    scores = _baseline_event_scores()
    row: dict = {"label": "Naive baseline"}
    for event in EVENTS:
        row[event] = scores[event]["brier"]
    row["rps"] = means_b["mean_brier_baseline"]
    row["rps_qf"] = means_b["mean_brier_baseline_from_qf"]
    row["log_loss"] = means_ll["mean_log_loss_baseline"]
    row["log_loss_qf"] = means_ll["mean_log_loss_baseline_from_qf"]
    return row


def _our_headline_row(sim: dict, strength: str, label: str) -> dict:
    cell = sim["strengths"][strength]["pre_tournament"]
    means_b = sim["tournament_mean_brier"][strength]
    means_ll = sim["tournament_mean_log_loss"][strength]
    row: dict = {"label": label}
    for event in EVENTS:
        row[event] = cell["events"][event]["brier"]
    row["rps"] = means_b["mean_brier"]
    row["rps_qf"] = means_b["mean_brier_from_qf"]
    row["log_loss"] = means_ll["mean_log_loss"]
    row["log_loss_qf"] = means_ll["mean_log_loss_from_qf"]
    return row


def _ace_headline_row(model: dict) -> dict:
    row: dict = {"label": model["label"]}
    brier = model.get("brier") or {}
    for event in EVENTS:
        row[event] = brier.get(event)
    row["rps"] = model.get("rps")
    row["rps_qf"] = model.get("rps_qf")
    row["log_loss"] = model.get("log_loss")
    row["log_loss_qf"] = model.get("log_loss_qf")
    return row


def _headline_rows(sim: dict, external: dict) -> list[dict]:
    rows = [
        _baseline_headline_row(sim),
        _our_headline_row(sim, "fifa", "Our sim - FIFA"),
        _our_headline_row(sim, "elo", "Our sim - Elo"),
    ]
    for model in external.get("models", []):
        rows.append(_ace_headline_row(model))
    return rows


def _md_table(headers: list[str], rows: list[list[str]], align: list[str]) -> str:
    head = "| " + " | ".join(headers) + " |"
    sep = "| " + " | ".join(align) + " |"
    body = "\n".join("| " + " | ".join(row) + " |" for row in rows)
    return f"{head}\n{sep}\n{body}"


def _match_table(match: dict) -> str:
    headers = [
        "Model",
        "2022 log-loss",
        "2022 Brier",
        "2026 log-loss",
        "2026 Brier",
    ]
    rows = []
    for key, label in (("fifa", "FIFA"), ("elo", "Elo")):
        block = match[key]
        y2022 = block["years"]["2022"]
        y2026 = block["years"]["2026"]
        rows.append(
            [
                label,
                _fmt(y2022["log_loss"]),
                _fmt(y2022["brier"]),
                _fmt(y2026["log_loss"]),
                _fmt(y2026["brier"]),
            ]
        )
    align = [":---"] + [":---:"] * (len(headers) - 1)
    return _md_table(headers, rows, align)


def _elo_ranks(teams: list[str]) -> tuple[dict[str, float], dict[str, int]]:
    ratings = json.loads(
        (ARTIFACTS_TRAINING / "elo_pre_tournament.json").read_text(encoding="utf-8")
    )["ratings"]
    values = {team: float(ratings.get(team, 1500.0)) for team in teams}
    ordered = sorted(values.items(), key=lambda item: (-item[1], item[0]))
    ranks = {team: idx + 1 for idx, (team, _) in enumerate(ordered)}
    return values, ranks


def _team_rows(sim: dict) -> list[dict]:
    teams = sim["strengths"]["elo"]["pre_tournament"]["teams"]
    values, ranks = _elo_ranks([row["team"] for row in teams])
    rows = []
    for row in teams:
        team = row["team"]
        out = {
            "label": team,
            "elo_rank": ranks[team],
            "elo": round(values[team]),
            "rps": row["mean_brier"],
            "rps_qf": row["mean_brier_from_qf"],
        }
        for event in EVENTS:
            p = float(row[f"p_{event}"])
            y = float(row[f"y_{event}"])
            out[event] = (p - y) ** 2
        rows.append(out)
    rows.sort(key=lambda row: (row["elo_rank"], row["label"]))
    return rows


def _headline_md(rows: list[dict]) -> str:
    sep = "│"
    headers = [
        "Model",
        *MD_HEADLINE_HEADERS[:N_STAGE_COLS],
        sep,
        *MD_HEADLINE_HEADERS[N_STAGE_COLS:],
    ]
    body = []
    for row in rows:
        body.append(
            [
                row["label"],
                *(_fmt(row[col]) for col in HEADLINE_COLS[:N_STAGE_COLS]),
                sep,
                *(_fmt(row[col]) for col in HEADLINE_COLS[N_STAGE_COLS:]),
            ]
        )
    align = [":---"] + [":---:"] * (len(headers) - 1)
    return _md_table(headers, body, align)


def _lerp(a: tuple[int, int, int], b: tuple[int, int, int], t: float) -> tuple[int, int, int]:
    return tuple(int(round(x + (y - x) * t)) for x, y in zip(a, b))


def _hex(rgb: tuple[int, int, int]) -> str:
    return "#{:02x}{:02x}{:02x}".format(*rgb)


def _cell_color(value: float | None, lo: float, hi: float) -> str:
    if value is None:
        return "#f3f4f6"
    if hi <= lo:
        return "#eef2e6"
    t = (value - lo) / (hi - lo)
    green = (198, 230, 201)
    mid = (245, 243, 238)
    red = (255, 205, 210)
    if t < 0.5:
        return _hex(_lerp(green, mid, t * 2))
    return _hex(_lerp(mid, red, (t - 0.5) * 2))


def _write_grid_svg(
    path: Path,
    rows: list[dict],
    *,
    aria: str,
    label_header: str,
    info_cols: list[tuple[str, str]],
    score_cols: list[str],
    score_headers: list[str],
    groups: list[tuple[str, int, int]],
    sep_cols: list[int],
) -> None:
    n_meta = 1 + len(info_cols)
    col_w = [196] + [114] * (len(info_cols) + len(score_cols))
    row_h = 48
    group_h = 36
    header_h = 50
    pad = 16
    legend_h = 28
    width = pad * 2 + sum(col_w)
    height = pad * 2 + legend_h + group_h + header_h + row_h * len(rows)
    ranges: dict[str, tuple[float, float]] = {}
    for col in score_cols:
        nums = [row[col] for row in rows if row[col] is not None]
        ranges[col] = (min(nums), max(nums)) if nums else (0.0, 0.0)

    y_group = pad + legend_h
    y_header = y_group + group_h
    y_data = y_header + header_h
    xs = [pad]
    for w in col_w[:-1]:
        xs.append(xs[-1] + w)
    x_end = pad + sum(col_w)

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}" role="img" aria-label="{escape(aria)}">',
        '<rect width="100%" height="100%" fill="#ffffff"/>',
        '<text x="16" y="22" font-size="13" fill="#6b7280" '
        'font-family="system-ui,sans-serif">Lower is better (green). Red is worse in that column.</text>',
    ]
    for title, start, end in groups:
        x0 = xs[start]
        x1 = x_end if end >= len(xs) else xs[end]
        parts.append(
            f'<text x="{(x0 + x1) / 2}" y="{y_group + 24}" text-anchor="middle" '
            f'font-size="18" font-weight="600" fill="#374151" '
            f'font-family="system-ui,sans-serif">{escape(title)}</text>'
        )
    headers = [label_header, *(header for _, header in info_cols), *score_headers]
    for header, x, w in zip(headers, xs, col_w):
        parts.append(
            f'<text x="{x + w / 2}" y="{y_header + 32}" text-anchor="middle" font-size="18" '
            f'font-weight="600" fill="#111827" font-family="system-ui,sans-serif">{escape(header)}</text>'
        )
    meta_keys = [key for key, _ in info_cols]
    for r, row in enumerate(rows):
        y = y_data + r * row_h
        parts.append(
            f'<rect x="{xs[0]}" y="{y}" width="{col_w[0]}" height="{row_h}" fill="#f8fafc" '
            f'stroke="#e5e7eb"/>'
        )
        parts.append(
            f'<text x="{xs[0] + 12}" y="{y + 31}" font-size="16" fill="#111827" '
            f'font-family="system-ui,sans-serif">{escape(row["label"])}</text>'
        )
        for i, key in enumerate(meta_keys):
            x = xs[1 + i]
            w = col_w[1 + i]
            parts.append(
                f'<rect x="{x}" y="{y}" width="{w}" height="{row_h}" fill="#f8fafc" '
                f'stroke="#e5e7eb"/>'
            )
            parts.append(
                f'<text x="{x + w / 2}" y="{y + 31}" text-anchor="middle" font-size="16" '
                f'fill="#111827" font-family="system-ui,sans-serif">{escape(str(row[key]))}</text>'
            )
        for i, col in enumerate(score_cols):
            x = xs[n_meta + i]
            w = col_w[n_meta + i]
            value = row[col]
            lo, hi = ranges[col]
            fill = _cell_color(value, lo, hi)
            parts.append(
                f'<rect x="{x}" y="{y}" width="{w}" height="{row_h}" fill="{fill}" '
                f'stroke="#e5e7eb"/>'
            )
            parts.append(
                f'<text x="{x + w / 2}" y="{y + 31}" text-anchor="middle" font-size="16" '
                f'fill="#111827" font-family="system-ui,sans-serif">{escape(_fmt(value))}</text>'
            )
    y_line_bottom = y_data + row_h * len(rows)
    table_w = sum(col_w)
    table_h = y_line_bottom - y_group
    stroke = "#111827"
    parts.append(
        f'<rect x="{pad}" y="{y_group}" width="{table_w}" height="{table_h}" '
        f'fill="none" stroke="{stroke}" stroke-width="2"/>'
    )
    parts.append(
        f'<line x1="{pad}" y1="{y_data}" x2="{pad + table_w}" y2="{y_data}" '
        f'stroke="{stroke}" stroke-width="2"/>'
    )
    for sep_col in sep_cols:
        parts.append(
            f'<line x1="{xs[sep_col]}" y1="{y_group}" x2="{xs[sep_col]}" '
            f'y2="{y_line_bottom}" stroke="{stroke}" stroke-width="2"/>'
        )
    parts.append("</svg>\n")
    path.write_text("".join(parts), encoding="utf-8")


def _write_headline_svg(rows: list[dict]) -> None:
    _write_grid_svg(
        SVG_PATH,
        rows,
        aria="Pre-tournament simulation scores, lower is better",
        label_header="Model",
        info_cols=[],
        score_cols=HEADLINE_COLS,
        score_headers=HEADLINE_HEADERS,
        groups=[
            ("Brier (per stage)", 1, 1 + N_STAGE_COLS),
            ("RPS = avg Brier", 1 + N_STAGE_COLS, 3 + N_STAGE_COLS),
            ("Log-loss (avg)", 3 + N_STAGE_COLS, 5 + N_STAGE_COLS),
        ],
        sep_cols=[1 + N_STAGE_COLS],
    )


def _write_team_svg(rows: list[dict]) -> None:
    _write_grid_svg(
        TEAM_SVG_PATH,
        rows,
        aria="Per-team Elo simulation Brier and RPS, lower is better",
        label_header="Team",
        info_cols=[("elo_rank", "Elo rank"), ("elo", "Elo")],
        score_cols=[*EVENTS, "rps", "rps_qf"],
        score_headers=[*(EVENT_LABELS[e] for e in EVENTS), "RPS", "RPS QF→"],
        groups=[
            ("Elo", 1, 3),
            ("Brier (per stage)", 3, 3 + N_STAGE_COLS),
            ("RPS = avg Brier", 3 + N_STAGE_COLS, 5 + N_STAGE_COLS),
        ],
        sep_cols=[3, 3 + N_STAGE_COLS],
    )


def write_evaluation_md() -> tuple[Path, Path, Path]:
    match = _load("match_metrics.json")
    sim = _load("simulation_metrics.json")
    external = _load("external_benchmarks.json")
    rows = _headline_rows(sim, external)
    team_rows = _team_rows(sim)
    _write_headline_svg(rows)
    _write_team_svg(team_rows)

    body = f"""# Evaluation results

Scores for the 2026 World Cup forecasts in this repo. Metric definitions: [evaluation.md](evaluation.md). 

Match and simulation numbers come from committed `match_metrics.json` and `simulation_metrics.json`. ACE Laboratory rows are transcribed from [their 2026 model comparison]({ACE_URL}) (Figures 3–5). Regenerate with `python scripts/write_evaluation_md.py` from `model/`.

Lower Brier, RPS, and log-loss are better. Per-stage columns are Brier scores. RPS is the average of those Briers (R32 through champion), matching ACE’s tournament RPS; RPS QF→ averages QF through champion. Log-loss columns use the same averaging.

## All-match evaluation

Pre-tournament strength models scored on all World Cup matches (three-way win/draw/lose).

{_match_table(match)}

## Full tournament simulation results

Naive baseline is equal-share chance (each of the 48 teams has probability *k*/48 of occupying one of *k* remaining slots). Our sim rows use pre-tournament Monte Carlo results. Stage columns are Brier; RPS is average Brier. 

{_headline_md(rows)}

The following diagram shows the same results in a color-coded visual grid.
The color scale is column-wise (green = best / lowest among shown models).

![Pre-tournament simulation scores](evaluation-headline.svg)

## Per-team RPS (Our sim - Elo)

Pre-tournament Elo simulation scored per country. Stage columns are that team’s Brier for each reach event. RPS is the average of those Briers (R32 through champion); RPS QF→ averages QF through champion. Teams are ordered by Elo rank. Color scale is column-wise (green = best / lowest among the 48 teams).

![Per-team Elo simulation RPS](evaluation-elo-teams.svg)
"""
    MD_PATH.write_text(body, encoding="utf-8")
    return MD_PATH, SVG_PATH, TEAM_SVG_PATH


def main() -> None:
    for path in write_evaluation_md():
        print(f"Wrote {path}")


if __name__ == "__main__":
    main()
