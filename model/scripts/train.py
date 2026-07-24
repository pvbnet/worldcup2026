#!/usr/bin/env python3
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from config import ARTIFACTS_TRAINING, STAGE_ORDER
from evaluate import evaluate_models
from ingest import load_matches, normalize_matches
from models.elo import fit_elo
from models.fifa import seed_ratings_from_fifa
from simulation.bracket import filter_training_matches


def main() -> None:
    normalize_matches()
    matches = load_matches()

    for stage in STAGE_ORDER:
        train_matches = filter_training_matches(matches, stage)
        teams = pd.unique(
            pd.concat([train_matches["team1"], train_matches["team2"]], ignore_index=True)
        )
        seeds = seed_ratings_from_fifa([str(t) for t in teams])
        elo = fit_elo(train_matches, base_ratings=seeds)
        elo.save(ARTIFACTS_TRAINING / f"elo_{stage}.json")
        print(f"Trained Elo for stage={stage}: {len(train_matches)} matches used.")

    metrics = evaluate_models(matches)
    print("Training complete (Elo only).")
    for name, values in metrics.items():
        print(f"  {name}: log_loss={values['mean_log_loss']:.4f}")


if __name__ == "__main__":
    main()
