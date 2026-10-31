"""Bootstrap confidence intervals for backtest savings.

Resampling whole PRODUCTS (not individual weeks) respects that weeks of one product are correlated.
"""
from __future__ import annotations

import random

from .simulator import BacktestReport


def _savings_pct(report: BacktestReport, policy: str, products: list[str]) -> float:
    always = sum(report.always_by_product[p] for p in products)
    spent = sum(report.results[policy].per_product[p] for p in products)
    return 100 * (always - spent) / always


def bootstrap_savings(report: BacktestReport, policy: str, n: int = 2000, seed: int = 0,
                      baseline: str | None = None) -> dict:
    """Point estimate and 95% interval of savings vs always-buy, or of the gap vs `baseline`."""
    rng = random.Random(seed)
    products = sorted(report.always_by_product)

    def stat(sample):
        s = _savings_pct(report, policy, sample)
        return s - _savings_pct(report, baseline, sample) if baseline else s

    point = stat(products)
    draws = sorted(stat([rng.choice(products) for _ in products]) for _ in range(n))
    return {"estimate": round(point, 2), "low": round(draws[int(0.025 * n)], 2),
            "high": round(draws[int(0.975 * n) - 1], 2)}
