#!/usr/bin/env python3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from evaluate import evaluate_models
from ingest import load_matches, normalize_matches
from models.elo import fit_elo


def main() -> None:
    normalize_matches()
    matches = load_matches()

    elo = fit_elo(matches)
    elo.save()

    metrics = evaluate_models(matches)
    print("Training complete (Elo only).")
    for name, values in metrics.items():
        print(f"  {name}: log_loss={values['mean_log_loss']:.4f}")


if __name__ == "__main__":
    main()
