"""Features and labels for predicting "will this item get meaningfully cheaper soon?".

Every feature uses only prices up to and including week t. Labels look into the future,
which is why the dataset builder must keep each label window out of the test period.
"""
from __future__ import annotations

import statistics

DROP = 0.10      # "meaningfully cheaper" means at least 10% below today's price
LOOKBACK = 12    # weeks of history used to judge the item's normal price

FEATURE_NAMES = [
    "ratio_to_recent_max",     # today vs the recent normal (regular) price
    "ratio_to_recent_median",
    "weeks_since_last_special",
    "typical_gap_weeks",       # how often this item usually goes on special
    "cycle_phase",             # weeks since last special / typical gap
    "recent_volatility",
    "is_perishable",
]


def _special_weeks(prices: list[float], t: int) -> list[int]:
    """Weeks (up to t) where the price was at least DROP below its trailing max: a special."""
    weeks = []
    for i in range(1, t + 1):
        ref = max(prices[max(0, i - LOOKBACK):i])
        if prices[i] <= ref * (1 - DROP):
            weeks.append(i)
    return weeks


def build_features(prices: list[float], t: int, perishable: bool) -> list[float]:
    window = prices[max(0, t - LOOKBACK + 1):t + 1]
    now = prices[t]
    recent_max, recent_median = max(window), statistics.median(window)

    specials = _special_weeks(prices, t)
    starts = [w for i, w in enumerate(specials) if i == 0 or w - specials[i - 1] > 1]
    since = t - specials[-1] if specials else t + 1
    gaps = [b - a for a, b in zip(starts, starts[1:])]
    typical_gap = statistics.median(gaps) if gaps else float(LOOKBACK)

    changes = [(b - a) / a for a, b in zip(window, window[1:]) if a > 0]
    volatility = statistics.pstdev(changes) if len(changes) > 1 else 0.0

    return [
        now / recent_max if recent_max else 1.0,
        now / recent_median if recent_median else 1.0,
        float(since),
        float(typical_gap),
        since / typical_gap if typical_gap else 0.0,
        volatility,
        1.0 if perishable else 0.0,
    ]


def label(prices: list[float], t: int, horizon: int) -> int | None:
    """1 if the price falls at least DROP below today's within the next `horizon` weeks."""
    future = prices[t + 1:t + 1 + horizon]
    if len(future) < horizon:
        return None  # not enough future to know the answer
    return int(min(future) <= prices[t] * (1 - DROP))
