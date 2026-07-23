#!/usr/bin/env python3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from ingest import load_matches
from models.elo import EloModel
from simulation.tournament import TournamentSimulator


def main() -> None:
    matches = load_matches()
    elo = EloModel.load()

    for strength in ("elo", "fifa"):
        simulator = TournamentSimulator(matches, elo, strength=strength)
        n_sims = 2000
        df = simulator.run(simulations=n_sims)
        simulator.save_predictions(df, strength, simulations=n_sims)
        top = df.iloc[0]
        print(
            f"{strength}: top pick {top['team']} "
            f"({top['p_win'] * 100:.1f}% win probability)"
        )


if __name__ == "__main__":
    main()
