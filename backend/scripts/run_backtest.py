"""Run the decision backtest.

    python scripts/run_backtest.py --synthetic            # develop and test the pipeline
    python scripts/run_backtest.py --csv data/prices.csv  # real observations (product_id,name,category,date,price)

Headline numbers should only ever come from real price data.
"""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.backtest.data import load_csv, synthetic_specials  # noqa: E402
from app.backtest.policies import (AlwaysBuy, DecisionEnginePolicy,  # noqa: E402
                                   DirectionCheckedEnginePolicy, RollingLowHeuristic)
from app.backtest.simulator import run_backtest  # noqa: E402

COLS = ["policy", "spend", "savings_vs_always_buy_pct", "share_of_oracle_savings_pct",
        "wait_rate_pct", "backfire_rate_pct", "avg_weeks_waited"]


def to_markdown(rows: list[dict]) -> str:
    fmt = lambda v: "-" if v is None else str(v)
    lines = ["| " + " | ".join(COLS) + " |", "|" + "---|" * len(COLS)]
    lines += ["| " + " | ".join(fmt(r[c]) for c in COLS) + " |" for r in rows]
    return "\n".join(lines)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    src = ap.add_mutually_exclusive_group(required=True)
    src.add_argument("--csv")
    src.add_argument("--synthetic", action="store_true")
    ap.add_argument("--products", type=int, default=40)
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--json-out")
    a = ap.parse_args()

    series = load_csv(a.csv) if a.csv else synthetic_specials(a.products, seed=a.seed)
    policies = [AlwaysBuy(), RollingLowHeuristic(), DecisionEnginePolicy(), DirectionCheckedEnginePolicy()]
    report = run_backtest(series, policies)
    rows = report.summary_rows()
    print(f"Source: {report.source} | products: {report.products} | purchase needs: {report.needs}")
    if report.source == "synthetic":
        print("WARNING: synthetic data. Use for development only, not for claims.")
    print(to_markdown(rows))
    if a.json_out:
        Path(a.json_out).write_text(json.dumps({"source": report.source, "needs": report.needs, "rows": rows}, indent=2))
