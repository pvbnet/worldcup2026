#!/usr/bin/env python3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from config import ARTIFACTS_TRAINING, STAGE_ORDER
from ingest import load_matches
from models.elo import EloModel
from simulation.bracket import RealBracketSimulator


def main() -> None:
    matches = load_matches()
    n_sims = 2000

    for stage in STAGE_ORDER:
        elo_path = ARTIFACTS_TRAINING / f"elo_{stage}.json"
        elo = EloModel.load(elo_path) if elo_path.exists() else EloModel.load()

        for strength in ("elo", "fifa"):
            simulator = RealBracketSimulator(matches, elo, strength=strength, stage=stage)
            df = simulator.run(simulations=n_sims)
            simulator.save_predictions(df, simulations=n_sims)
            top = df.iloc[0]
            print(
                f"stage={stage} strength={strength}: top pick {top['team']} "
                f"({top['p_win'] * 100:.1f}% win probability)"
            )


if __name__ == "__main__":
    main()
