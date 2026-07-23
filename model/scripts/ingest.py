#!/usr/bin/env python3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from ingest import normalize_matches


def main() -> None:
    df = normalize_matches()
    print(f"Ingested {len(df)} matches ({int(df['played'].sum())} played)")


if __name__ == "__main__":
    main()
