import json
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import urlopen

import pandas as pd

from config import (
    ALL_YEARS,
    COMPETITION_SOURCES,
    COMPETITION_WEIGHTS,
    DATA_PROCESSED,
    DATA_RAW,
    OPENFOOTBALL_BASE,
)
from sources.footballtxt import fetch_competition_edition
from teams import canonicalize, is_placeholder


def fetch_year(year: int, force: bool = True) -> Path:
    dest = DATA_RAW / f"{year}.json"
    if dest.exists() and not force:
        return dest
    url = f"{OPENFOOTBALL_BASE}/{year}/worldcup.json"
    with urlopen(url, timeout=60) as response:
        payload = json.loads(response.read().decode("utf-8"))
    dest.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return dest


def infer_stage(round_name: str, group: str | None) -> str:
    text = (round_name or "").lower()
    if "3rd" in text or "third" in text:
        return "third"
    if "final" in text and "semi" not in text and "quarter" not in text:
        return "final"
    if "semi" in text:
        return "sf"
    if "quarter" in text:
        return "qf"
    if "round of 32" in text:
        return "r32"
    if "round of 16" in text or "last 16" in text:
        return "r16"
    if group:
        return "group"
    return "knockout"


def _append_matches_from_payload(
    rows: list[dict],
    payload: dict,
    *,
    competition: str,
    default_stage: str | None = None,
    year_override: int | None = None,
) -> None:
    weight = COMPETITION_WEIGHTS.get(competition, 1.0)
    for match in payload.get("matches", []):
        team1 = canonicalize(match.get("team1", ""))
        team2 = canonicalize(match.get("team2", ""))
        if is_placeholder(team1) or is_placeholder(team2):
            continue

        score = match.get("score") or {}
        ft = score.get("ft")
        played = ft is not None and len(ft) == 2
        goals1 = int(ft[0]) if played else None
        goals2 = int(ft[1]) if played else None

        def _score_pair(key: str) -> tuple[int | None, int | None]:
            val = score.get(key)
            if val is not None and len(val) == 2:
                return int(val[0]), int(val[1])
            return None, None

        et1, et2 = _score_pair("et")
        pen1, pen2 = _score_pair("p")

        advancer: str | None = None
        if played:
            if pen1 is not None and pen2 is not None and pen1 != pen2:
                advancer = team1 if pen1 > pen2 else team2
            elif et1 is not None and et2 is not None and et1 != et2:
                advancer = team1 if et1 > et2 else team2
            elif goals1 is not None and goals2 is not None and goals1 != goals2:
                advancer = team1 if goals1 > goals2 else team2

        date = match.get("date")
        if year_override is not None:
            year = year_override
        elif date and len(str(date)) >= 4 and str(date)[:4].isdigit():
            year = int(str(date)[:4])
        else:
            year = payload.get("edition")

        if default_stage is not None:
            stage = default_stage
        else:
            stage = infer_stage(match.get("round", ""), match.get("group"))

        rows.append(
            {
                "year": year,
                "date": date,
                "round": match.get("round"),
                "group": match.get("group"),
                "stage": stage,
                "team1": team1,
                "team2": team2,
                "goals1": goals1,
                "goals2": goals2,
                "et1": et1,
                "et2": et2,
                "pen1": pen1,
                "pen2": pen2,
                "advancer": advancer,
                "played": played,
                "ground": match.get("ground"),
                "competition": competition,
                "weight": weight,
            }
        )


def normalize_matches(years: list[int] | None = None) -> pd.DataFrame:
    years = years or ALL_YEARS
    rows: list[dict] = []

    for year in years:
        raw_path = DATA_RAW / f"{year}.json"
        if not raw_path.exists():
            fetch_year(year)
        payload = json.loads(raw_path.read_text(encoding="utf-8"))
        _append_matches_from_payload(
            rows,
            payload,
            competition="world_cup",
            year_override=year,
        )

    for competition, meta in COMPETITION_SOURCES.items():
        for edition in meta["editions"]:
            raw_path = DATA_RAW / meta["raw_subdir"] / f"{edition}.json"
            if not raw_path.exists():
                fetch_competition_edition(competition, edition)
            payload = json.loads(raw_path.read_text(encoding="utf-8"))
            _append_matches_from_payload(
                rows,
                payload,
                competition=competition,
                default_stage=meta.get("default_stage"),
            )

    df = pd.DataFrame(rows)
    if df.empty:
        raise RuntimeError("No matches ingested")

    df["match_id"] = (
        df["competition"].astype(str)
        + "_"
        + df["year"].astype(str)
        + "_"
        + df["team1"]
        + "_"
        + df["team2"]
        + "_"
        + df["date"].astype(str)
    )
    out = DATA_PROCESSED / "matches.parquet"
    df.to_parquet(out, index=False)

    by_competition = {
        str(comp): int(count)
        for comp, count in df.groupby("competition").size().items()
    }
    meta = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "years": years,
        "match_count": len(df),
        "played_count": int(df["played"].sum()),
        "by_competition": by_competition,
    }
    (DATA_PROCESSED / "matches_meta.json").write_text(
        json.dumps(meta, indent=2), encoding="utf-8"
    )
    return df


def load_matches() -> pd.DataFrame:
    path = DATA_PROCESSED / "matches.parquet"
    if not path.exists():
        return normalize_matches()
    return pd.read_parquet(path)
