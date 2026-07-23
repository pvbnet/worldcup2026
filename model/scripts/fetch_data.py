#!/usr/bin/env python3
"""Download World Cup + continental/qualifier match data into model/data/raw/."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from config import ALL_YEARS, COMPETITION_SOURCES, DATA_RAW
from ingest import fetch_year
from sources.footballtxt import fetch_all_competitions


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Download raw match JSON for World Cup and international competitions."
    )
    parser.add_argument(
        "--competitions",
        nargs="+",
        choices=["world_cup", *COMPETITION_SOURCES.keys()],
        help="Subset of competitions to download (default: all).",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Re-download even when local raw JSON already exists.",
    )
    args = parser.parse_args()

    selected = args.competitions or ["world_cup", *COMPETITION_SOURCES.keys()]

    if "world_cup" in selected:
        for year in ALL_YEARS:
            path = DATA_RAW / f"{year}.json"
            if path.exists() and not args.force:
                print(f"world_cup {year}: cached {path}")
            else:
                dest = fetch_year(year, force=True)
                print(f"world_cup {year}: wrote {dest}")

    others = [c for c in selected if c != "world_cup"]
    if others:
        results = fetch_all_competitions(competitions=others, force=args.force)
        for competition, paths in results.items():
            for path in paths:
                print(f"{competition}: wrote {path}")


if __name__ == "__main__":
    main()
