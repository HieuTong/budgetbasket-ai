"""Replays price history for a simulated household and scores each policy's purchase timing.

Model: a product is needed every `need_every_weeks`. When a need arises at week t, the policy
may WAIT up to `max_wait` weeks (shorter for perishables); at the deadline it must buy.
The oracle buys at the cheapest week in that window with perfect hindsight, which sets the
ceiling on achievable savings.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from .data import WeeklySeries
from .policies import Policy

PERISHABLE = {"produce", "meat", "dairy", "bakery", "seafood", "deli"}


def max_wait_for(category: str, perishable_wait: int = 1, pantry_wait: int = 4) -> int:
    return perishable_wait if category.lower() in PERISHABLE else pantry_wait


@dataclass
class PolicyResult:
    name: str
    spend: float = 0.0
    needs: int = 0
    waits: int = 0           # needs where the policy delayed at least one week
    backfires: int = 0       # delayed, then paid more than the price when the need arose
    weeks_waited: int = 0
    per_category: dict = field(default_factory=dict)
    per_product: dict = field(default_factory=dict)  # product_id -> spend, used for bootstrap intervals


@dataclass
class BacktestReport:
    results: dict[str, PolicyResult]
    oracle_spend: float
    always_buy_spend: float
    needs: int
    products: int
    source: str
    always_by_product: dict = field(default_factory=dict)
    oracle_by_product: dict = field(default_factory=dict)

    def summary_rows(self) -> list[dict]:
        rows = []
        achievable = self.always_buy_spend - self.oracle_spend
        for r in self.results.values():
            saved = self.always_buy_spend - r.spend
            rows.append({
                "policy": r.name,
                "spend": round(r.spend, 2),
                "savings_vs_always_buy_pct": round(100 * saved / self.always_buy_spend, 2),
                "share_of_oracle_savings_pct": round(100 * saved / achievable, 1) if achievable > 0 else None,
                "wait_rate_pct": round(100 * r.waits / r.needs, 1) if r.needs else 0.0,
                "backfire_rate_pct": round(100 * r.backfires / r.waits, 1) if r.waits else 0.0,
                "avg_weeks_waited": round(r.weeks_waited / r.needs, 2) if r.needs else 0.0,
            })
        rows.append({
            "policy": "oracle (perfect hindsight)",
            "spend": round(self.oracle_spend, 2),
            "savings_vs_always_buy_pct": round(100 * achievable / self.always_buy_spend, 2),
            "share_of_oracle_savings_pct": 100.0 if achievable > 0 else None,
            "wait_rate_pct": None, "backfire_rate_pct": None, "avg_weeks_waited": None,
        })
        return rows


def run_backtest(series: list[WeeklySeries], policies: list[Policy], *, warmup_weeks: int = 8,
                 need_every_weeks: int = 2, perishable_wait: int = 1, pantry_wait: int = 4) -> BacktestReport:
    if not series:
        raise ValueError("No price series to backtest")
    results = {p.name: PolicyResult(p.name) for p in policies}
    oracle = always = 0.0
    needs = 0
    always_by: dict[str, float] = {}
    oracle_by: dict[str, float] = {}
    for s in series:
        max_wait = max_wait_for(s.category, perishable_wait, pantry_wait)
        last = len(s.prices) - 1
        for t in range(warmup_weeks, last + 1, need_every_weeks):
            deadline = min(t + max_wait, last)
            window = s.prices[t:deadline + 1]
            oracle += min(window)
            always += s.prices[t]
            always_by[s.product_id] = always_by.get(s.product_id, 0.0) + s.prices[t]
            oracle_by[s.product_id] = oracle_by.get(s.product_id, 0.0) + min(window)
            needs += 1
            for p in policies:
                week = t
                while week < deadline and p.decide(s.dates[:week + 1], s.prices[:week + 1]) == "WAIT":
                    week += 1
                paid = s.prices[week]
                r = results[p.name]
                r.spend += paid
                r.needs += 1
                r.weeks_waited += week - t
                if week > t:
                    r.waits += 1
                    if paid > s.prices[t] + 1e-9:
                        r.backfires += 1
                cat = r.per_category.setdefault(s.category, {"spend": 0.0, "needs": 0})
                cat["spend"] += paid
                cat["needs"] += 1
                r.per_product[s.product_id] = r.per_product.get(s.product_id, 0.0) + paid
    sources = {s.source for s in series}
    return BacktestReport(results, oracle, always, needs, len(series), "+".join(sorted(sources)),
                          always_by, oracle_by)
