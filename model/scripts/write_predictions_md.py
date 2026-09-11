#!/usr/bin/env python3
"""Write docs/predictions.md from committed pre-tournament prediction JSON."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from xml.sax.saxutils import escape

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from config import ARTIFACTS_PREDICTIONS, ARTIFACTS_TRAINING, PROJECT_ROOT
from models.elo import EloModel
from models.fifa import load_fifa_snapshot, rank_lookup, rank_table_from_values

OUT_PATH = PROJECT_ROOT / "docs" / "predictions.md"
ELO_SVG_PATH = PROJECT_ROOT / "docs" / "predictions-elo.svg"
DASHBOARD_URL = "https://worldcup2026-dashboard.web.app/"
PROB_COLS = [
    ("p_r32", "P(R32)"),
    ("p_r16", "P(R16)"),
    ("p_qf", "P(QF)"),
    ("p_sf", "P(SF)"),
    ("p_final", "P(Final)"),
    ("p_win", "P(Win)"),
]
SKY_ICE = (232, 244, 252)
SKY_MID = (91, 163, 217)
SKY_NAVY = (30, 77, 140)


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


def _lerp(a: tuple[int, int, int], b: tuple[int, int, int], t: float) -> tuple[int, int, int]:
    return tuple(int(round(x + (y - x) * t)) for x, y in zip(a, b))


def _hex(rgb: tuple[int, int, int]) -> str:
    return "#{:02x}{:02x}{:02x}".format(*rgb)


def _sky_color(value: float, hi: float) -> tuple[str, str]:
    """Sequential ice → navy. Scale from 0 to this column's max. Darker = more likely."""
    if hi <= 0:
        rgb = SKY_ICE
    else:
        t = min(max(value / hi, 0.0), 1.0)
        if t < 0.5:
            rgb = _lerp(SKY_ICE, SKY_MID, t * 2)
        else:
            rgb = _lerp(SKY_MID, SKY_NAVY, (t - 0.5) * 2)
    luma = 0.299 * rgb[0] + 0.587 * rgb[1] + 0.114 * rgb[2]
    text = "#ffffff" if luma < 145 else "#111827"
    return _hex(rgb), text


def _write_elo_svg(payload: dict, elo: EloModel) -> Path:
    teams = [row["team"] for row in payload.get("teams", [])]
    elo_ranks = rank_table_from_values(
        {team: elo.ratings.get(team, 1500.0) for team in teams}
    )
    rows = sorted(payload.get("teams", []), key=lambda r: int(r.get("rank", 999)))
    maxima = {
        key: max(float(row.get(key, 0.0)) for row in rows) if rows else 0.0
        for key, _ in PROB_COLS
    }

    label_w = 220
    meta_w = 90
    prob_w = 102
    col_w = [label_w, meta_w, meta_w] + [prob_w] * len(PROB_COLS)
    row_h = 40
    group_h = 36
    header_h = 44
    pad = 16
    legend_h = 28
    width = pad * 2 + sum(col_w)
    height = pad * 2 + legend_h + group_h + header_h + row_h * len(rows)

    y_group = pad + legend_h
    y_header = y_group + group_h
    y_data = y_header + header_h
    xs = [pad]
    for w in col_w[:-1]:
        xs.append(xs[-1] + w)
    table_w = sum(col_w)
    y_bottom = y_data + row_h * len(rows)

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}" role="img" '
        f'aria-label="Pre-tournament Elo stage-reach and win probabilities">',
        '<rect width="100%" height="100%" fill="#ffffff"/>',
        '<text x="16" y="22" font-size="13" fill="#6b7280" '
        'font-family="system-ui,sans-serif">'
        "Darker blue is more likely. Each column is scaled from 0% to that column’s max."
        "</text>",
        f'<text x="{(xs[1] + xs[3]) / 2}" y="{y_group + 24}" '
        'text-anchor="middle" font-size="18" font-weight="600" fill="#374151" '
        'font-family="system-ui,sans-serif">Elo</text>',
        f'<text x="{xs[3] + (sum(col_w[3:]) / 2)}" y="{y_group + 24}" '
        'text-anchor="middle" font-size="18" font-weight="600" fill="#374151" '
        'font-family="system-ui,sans-serif">Stage-reach probability</text>',
    ]
    headers = ["Team", "Elo rank", "Elo", *(label for _, label in PROB_COLS)]
    for header, x, w in zip(headers, xs, col_w):
        parts.append(
            f'<text x="{x + w / 2}" y="{y_header + 30}" text-anchor="middle" font-size="16" '
            f'font-weight="600" fill="#111827" font-family="system-ui,sans-serif">'
            f"{escape(header)}</text>"
        )

    for r, row in enumerate(rows):
        y = y_data + r * row_h
        team = row["team"]
        parts.append(
            f'<rect x="{xs[0]}" y="{y}" width="{col_w[0]}" height="{row_h}" '
            f'fill="#f8fafc" stroke="#e5e7eb"/>'
        )
        parts.append(
            f'<text x="{xs[0] + 12}" y="{y + 26}" font-size="15" fill="#111827" '
            f'font-family="system-ui,sans-serif">{escape(team)}</text>'
        )
        meta = (
            str(elo_ranks.get(team, 999)),
            str(round(float(row.get("rating", 1500.0)))),
        )
        for i, value in enumerate(meta):
            x = xs[1 + i]
            w = col_w[1 + i]
            parts.append(
                f'<rect x="{x}" y="{y}" width="{w}" height="{row_h}" fill="#f8fafc" '
                f'stroke="#e5e7eb"/>'
            )
            parts.append(
                f'<text x="{x + w / 2}" y="{y + 26}" text-anchor="middle" font-size="15" '
                f'fill="#111827" font-family="system-ui,sans-serif">{escape(value)}</text>'
            )
        for i, (key, _) in enumerate(PROB_COLS):
            x = xs[3 + i]
            w = col_w[3 + i]
            p = float(row.get(key, 0.0))
            fill, text = _sky_color(p, maxima[key])
            parts.append(
                f'<rect x="{x}" y="{y}" width="{w}" height="{row_h}" fill="{fill}" '
                f'stroke="#e5e7eb"/>'
            )
            parts.append(
                f'<text x="{x + w / 2}" y="{y + 26}" text-anchor="middle" font-size="15" '
                f'fill="{text}" font-family="system-ui,sans-serif">{p * 100:.1f}%</text>'
            )

    stroke = "#111827"
    parts.append(
        f'<rect x="{pad}" y="{y_group}" width="{table_w}" height="{y_bottom - y_group}" '
        f'fill="none" stroke="{stroke}" stroke-width="2"/>'
    )
    parts.append(
        f'<line x1="{pad}" y1="{y_data}" x2="{pad + table_w}" y2="{y_data}" '
        f'stroke="{stroke}" stroke-width="2"/>'
    )
    parts.append(
        f'<line x1="{xs[3]}" y1="{y_group}" x2="{xs[3]}" y2="{y_bottom}" '
        f'stroke="{stroke}" stroke-width="2"/>'
    )
    parts.append("</svg>\n")
    ELO_SVG_PATH.write_text("".join(parts), encoding="utf-8")
    return ELO_SVG_PATH


def write_predictions_md() -> tuple[Path, Path]:
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
    svg_path = _write_elo_svg(elo_payload, elo)
    return OUT_PATH, svg_path


def main() -> None:
    for path in write_predictions_md():
        print(f"Wrote {path}")


if __name__ == "__main__":
    main()
