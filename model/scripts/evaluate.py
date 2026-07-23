#!/usr/bin/env python3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from evaluate import evaluate_models
from features.build import build_training_frame
from ingest import load_matches


def main() -> None:
    matches = load_matches()
    training_frame = build_training_frame(matches)
    metrics = evaluate_models(matches, training_frame)
    print("Evaluation complete.")
    for model, values in metrics.items():
        print(
            f"  {model}: mean_log_loss={values['mean_log_loss']:.4f}, "
            f"mean_brier={values['mean_brier']:.4f}"
        )


if __name__ == "__main__":
    main()
