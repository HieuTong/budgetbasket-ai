"""Train the specials model and compare every policy on unseen weeks, with 95% intervals.

    python scripts/run_specials_experiment.py --synthetic
    python scripts/run_specials_experiment.py --csv data/prices.csv
"""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.backtest.data import load_csv, synthetic_specials  # noqa: E402
from app.backtest.experiment import run_experiment  # noqa: E402

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    src = ap.add_mutually_exclusive_group(required=True)
    src.add_argument("--csv")
    src.add_argument("--synthetic", action="store_true")
    ap.add_argument("--products", type=int, default=60)
    ap.add_argument("--weeks", type=int, default=104)
    ap.add_argument("--seed", type=int, default=7)
    a = ap.parse_args()

    series = load_csv(a.csv) if a.csv else synthetic_specials(a.products, weeks=a.weeks, seed=a.seed)
    out = run_experiment(series, seed=a.seed)
    rep = out["report"]

    print(f"Source: {rep.source} | products: {rep.products} | trained on weeks 0-{out['split_week'] - 1}, "
          f"tested on the next {out['test_weeks']} weeks | WAIT threshold (tuned on training data): {out['threshold']}")
    if rep.source == "synthetic":
        print("WARNING: synthetic data was generated WITH regular specials cycles, which flatters a cycle model.")
    c = out["classification"]
    print(f"\nModel on unseen weeks: AUC {c['auc']} | Brier {c['brier']} vs {c['brier_baseline']} "
          f"for always guessing the base rate ({c['base_rate']})")
    print("Coefficients (standardised):", json.dumps(out["coefficients"]))

    print("\n| policy | savings vs always buying (95% interval) | wait rate | waits that backfired |")
    print("|---|---|---|---|")
    for row in rep.summary_rows():
        name = row["policy"]
        ci = out["intervals"].get(name)
        sav = f"{ci['estimate']}% ({ci['low']} to {ci['high']})" if ci else f"{row['savings_vs_always_buy_pct']}%"
        wr = "-" if row["wait_rate_pct"] is None else f"{row['wait_rate_pct']}%"
        bf = "-" if row["backfire_rate_pct"] is None else f"{row['backfire_rate_pct']}%"
        print(f"| {name} | {sav} | {wr} | {bf} |")
    d = out["model_vs_heuristic"]
    print(f"\nModel minus rolling-low heuristic: {d['estimate']} points (95% interval {d['low']} to {d['high']})")
