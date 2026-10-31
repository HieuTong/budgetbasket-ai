"""Price series for backtesting: load real observations from CSV, or generate a labelled synthetic set."""
from __future__ import annotations

import csv
import random
import statistics
from collections import defaultdict
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path


@dataclass
class WeeklySeries:
    product_id: str
    name: str
    category: str
    dates: list[date]
    prices: list[float]
    source: str  # "csv" or "synthetic"

    def __post_init__(self) -> None:
        if len(self.dates) != len(self.prices):
            raise ValueError(f"{self.product_id}: dates and prices differ in length")


def load_csv(path: str | Path, min_weeks: int = 16) -> list[WeeklySeries]:
    """Read rows of product_id,name,category,date(YYYY-MM-DD),price and aggregate to weekly medians.

    Weeks are anchored to the earliest date in the whole file, so every product shares one calendar.
    Weeks with no observation are filled with the previous week's price (and counted).
    """
    rows: dict[str, list[tuple[date, float]]] = defaultdict(list)
    meta: dict[str, tuple[str, str]] = {}
    with open(path, newline="") as fh:
        for r in csv.DictReader(fh):
            pid = r["product_id"].strip()
            rows[pid].append((date.fromisoformat(r["date"].strip()), float(r["price"])))
            meta[pid] = (r.get("name", pid).strip(), r.get("category", "unknown").strip().lower())
    if not rows:
        return []
    start = min(d for obs in rows.values() for d, _ in obs)
    series: list[WeeklySeries] = []
    for pid, obs in rows.items():
        buckets: dict[int, list[float]] = defaultdict(list)
        for d, p in obs:
            if p > 0:
                buckets[(d - start).days // 7].append(p)
        if not buckets:
            continue
        first, last = min(buckets), max(buckets)
        prices, dates, prev = [], [], None
        for w in range(first, last + 1):
            if buckets.get(w):
                prev = statistics.median(buckets[w])
            prices.append(prev)
            dates.append(start + timedelta(weeks=w))
        if len(prices) >= min_weeks:
            name, cat = meta[pid]
            series.append(WeeklySeries(pid, name, cat, dates, prices, "csv"))
    return series


def synthetic_specials(n_products: int = 40, weeks: int = 78, seed: int = 7) -> list[WeeklySeries]:
    """SYNTHETIC data for developing and testing the backtest, never for headline results.

    Each product has a regular price that drifts slowly, and goes on a temporary special
    (20-50% off for 1-2 weeks) on a rough cycle with random jitter, then returns to normal.
    """
    rng = random.Random(seed)
    categories = ["pantry", "pantry", "household", "dairy", "produce", "meat"]
    start = date(2025, 1, 6)
    out = []
    for i in range(n_products):
        cat = rng.choice(categories)
        base = round(rng.uniform(2.0, 15.0), 2)
        cycle = rng.randint(4, 10)
        depth = rng.uniform(0.20, 0.50)
        next_special = rng.randint(1, cycle)
        regular, prices, remaining = base, [], 0
        for w in range(weeks):
            regular = max(0.5, regular * (1 + rng.uniform(-0.004, 0.006)))
            if remaining == 0 and w >= next_special:
                remaining = rng.choice([1, 1, 2])
                next_special = w + cycle + rng.randint(-1, 2)
            price = regular * (1 - depth) if remaining > 0 else regular
            remaining = max(0, remaining - 1)
            prices.append(round(price * (1 + rng.uniform(-0.01, 0.01)), 2))
        out.append(WeeklySeries(f"syn_{i:03d}", f"Synthetic item {i}", cat,
                                [start + timedelta(weeks=w) for w in range(weeks)], prices, "synthetic"))
    return out
