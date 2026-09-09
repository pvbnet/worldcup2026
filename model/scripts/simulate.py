#!/usr/bin/env python3
"""Run Monte Carlo for every stage × strength and write prediction JSON."""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from config import ARTIFACTS_TRAINING, DEFAULT_SIMULATIONS, STAGE_ORDER
from evaluate_simulation import evaluate_simulations, print_simulation_summary
from ingest import load_matches
from models.elo import EloModel
from simulation.bracket import RealBracketSimulator


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run Monte Carlo for every stage × strength and write prediction JSON."
    )
    parser.add_argument(
        "-n",
        "--simulations",
        type=int,
        default=DEFAULT_SIMULATIONS,
        help=f"Monte Carlo trial count (default: {DEFAULT_SIMULATIONS})",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    matches = load_matches()
    n_sims = args.simulations

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

    print_simulation_summary(evaluate_simulations(matches))


if __name__ == "__main__":
    main()
