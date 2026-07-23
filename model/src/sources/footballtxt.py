"""Parse openfootball Football.TXT files into worldcup.json-compatible payloads."""

from __future__ import annotations

import json
import re
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import urlopen

from config import COMPETITION_SOURCES, DATA_RAW, INTERNATIONALS_BASE

MONTHS = {
    "Jan": 1,
    "Feb": 2,
    "Mar": 3,
    "Apr": 4,
    "May": 5,
    "Jun": 6,
    "Jul": 7,
    "Aug": 8,
    "Sep": 9,
    "Oct": 10,
    "Nov": 11,
    "Dec": 12,
}

DATE_RE = re.compile(
    r"^(Mon|Tue|Wed|Thu|Fri|Sat|Sun)\s+"
    r"(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+"
    r"(\d{1,2})\s*$"
)
SECTION_RE = re.compile(r"^▪\s+(.+?)\s*$")
TITLE_RE = re.compile(r"^=\s+(.+?)\s*$")
SCORED_RE = re.compile(
    r"^\s*(.+?)\s+(\d+)\s*-\s*(\d+)\s+(.+?)"
    r"(?:\s+@\s+(.+?))?(?:\s+\[.+\])?\s*$"
)
UNPLAYED_RE = re.compile(
    r"^\s*(.+?)\s+v(?:s\.?)?\s+(.+?)"
    r"(?:\s+@\s+(.+?))?\s*$"
)
GOAL_DETAIL_RE = re.compile(r"^\s+\(")


def _clean_team(name: str) -> str:
    return re.sub(r"\s+", " ", name).strip()


def parse_football_txt(text: str, file_year: int, name: str | None = None) -> dict:
    """Convert a Football.TXT document into {"name", "matches": [...]}."""
    matches: list[dict] = []
    current_date: str | None = None
    current_round: str | None = None
    current_group: str | None = None
    year = file_year
    last_month: int | None = None
    title = name

    for raw_line in text.splitlines():
        line = raw_line.rstrip()
        if not line.strip():
            continue
        if line.lstrip().startswith("#"):
            continue
        if GOAL_DETAIL_RE.match(line):
            continue

        title_match = TITLE_RE.match(line)
        if title_match:
            if title is None:
                title = title_match.group(1).strip()
            continue

        section_match = SECTION_RE.match(line)
        if section_match:
            section = section_match.group(1).strip()
            if "group" in section.lower():
                current_group = section
                current_round = section
            else:
                current_group = None
                current_round = section
            continue

        date_match = DATE_RE.match(line.strip())
        if date_match:
            month_name = date_match.group(2)
            day = int(date_match.group(3))
            month = MONTHS[month_name]
            if last_month is not None and last_month == 12 and month == 1:
                year += 1
            last_month = month
            current_date = f"{year:04d}-{month:02d}-{day:02d}"
            continue

        scored = SCORED_RE.match(line)
        if scored:
            team1 = _clean_team(scored.group(1))
            goals1 = int(scored.group(2))
            goals2 = int(scored.group(3))
            team2 = _clean_team(scored.group(4))
            ground = (scored.group(5) or "").strip() or None
            match: dict = {
                "date": current_date,
                "team1": team1,
                "team2": team2,
                "score": {"ft": [goals1, goals2]},
            }
            if current_round:
                match["round"] = current_round
            if current_group:
                match["group"] = current_group
            if ground:
                match["ground"] = ground
            matches.append(match)
            continue

        unplayed = UNPLAYED_RE.match(line)
        if unplayed:
            team1 = _clean_team(unplayed.group(1))
            team2 = _clean_team(unplayed.group(2))
            ground = (unplayed.group(3) or "").strip() or None
            match = {
                "date": current_date,
                "team1": team1,
                "team2": team2,
                "score": {},
            }
            if current_round:
                match["round"] = current_round
            if current_group:
                match["group"] = current_group
            if ground:
                match["ground"] = ground
            matches.append(match)

    return {"name": title or f"Tournament {file_year}", "matches": matches}


def download_text(url: str, timeout: int = 60) -> str:
    with urlopen(url, timeout=timeout) as response:
        return response.read().decode("utf-8")


def fetch_txt_file(folder: str, file_stem: str, file_year: int) -> str:
    url = f"{INTERNATIONALS_BASE}/{folder}/{file_year}_{file_stem}.txt"
    try:
        return download_text(url)
    except HTTPError as exc:
        raise FileNotFoundError(f"Failed to download {url}: HTTP {exc.code}") from exc
    except URLError as exc:
        raise ConnectionError(f"Failed to download {url}: {exc.reason}") from exc


def fetch_competition_edition(
    competition: str,
    edition: int,
    force: bool = False,
) -> Path:
    """Download and merge source TXT files for one competition edition into raw JSON."""
    meta = COMPETITION_SOURCES[competition]
    dest = DATA_RAW / meta["raw_subdir"] / f"{edition}.json"
    if dest.exists() and not force:
        return dest

    file_years: list[int] = meta["editions"][edition]
    merged_matches: list[dict] = []
    display = meta["display_name"]
    for file_year in file_years:
        text = fetch_txt_file(meta["folder"], meta["file_stem"], file_year)
        payload = parse_football_txt(
            text,
            file_year=file_year,
            name=f"{display} {edition}",
        )
        merged_matches.extend(payload["matches"])

    out = {
        "name": f"{display} {edition}",
        "competition": competition,
        "edition": edition,
        "source_years": file_years,
        "matches": merged_matches,
    }
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(out, indent=2), encoding="utf-8")
    return dest


def fetch_all_competitions(
    competitions: list[str] | None = None,
    force: bool = False,
) -> dict[str, list[Path]]:
    selected = competitions or list(COMPETITION_SOURCES.keys())
    results: dict[str, list[Path]] = {}
    for competition in selected:
        if competition not in COMPETITION_SOURCES:
            raise ValueError(f"Unknown competition: {competition}")
        paths: list[Path] = []
        for edition in COMPETITION_SOURCES[competition]["editions"]:
            paths.append(fetch_competition_edition(competition, edition, force=force))
        results[competition] = paths
    return results
