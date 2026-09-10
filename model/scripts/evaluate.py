#!/usr/bin/env python3
"""Score WC match backtests and 2026 simulation artifacts; write evaluation JSON."""

import sys
from pathlib import Path

_SCRIPTS = Path(__file__).resolve().parent
sys.path.insert(0, str(_SCRIPTS))
sys.path.insert(0, str(_SCRIPTS.parent / "src"))

from evaluate_matches import evaluate_matches
from evaluate_simulation import evaluate_simulations, print_simulation_summary
from ingest import load_matches
from write_evaluation_md import write_evaluation_md


def main() -> None:
    matches = load_matches()
    metrics = evaluate_matches(matches)
    print("Evaluation complete.")
    for model, values in metrics.items():
        print(
            f"  {model}: mean_log_loss={values['mean_log_loss']:.4f}, "
            f"mean_brier={values['mean_brier']:.4f}"
        )
    sim_metrics = evaluate_simulations(matches)
    print_simulation_summary(sim_metrics)
    for path in write_evaluation_md():
        print(f"Wrote {path}")


if __name__ == "__main__":
    main()
