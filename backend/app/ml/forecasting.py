"""
Lightweight price trend signal: 'buy now vs wait'.

Uses simple linear regression on recent price history as the MVP —
easy to explain, no heavy dependency. Documented upgrade path to
Prophet/XGBoost with lag features once there's enough history per
product to justify it (cite this trade-off in interviews: don't
reach for a heavy model before the data volume supports it).
"""
from dataclasses import dataclass
from datetime import datetime

import numpy as np


@dataclass
class PricePoint:
    price: float
    recorded_at: datetime


def price_trend(history: list[PricePoint]) -> dict:
    if len(history) < 2:
        return {"trend": "unknown", "confidence": 0.0, "recommendation": "insufficient_data"}

    history = sorted(history, key=lambda p: p.recorded_at)
    t0 = history[0].recorded_at
    x = np.array([(p.recorded_at - t0).days for p in history], dtype=float)
    y = np.array([p.price for p in history])

    slope, intercept = np.polyfit(x, y, 1)
    residuals = y - (slope * x + intercept)
    ss_res = float(np.sum(residuals**2))
    ss_tot = float(np.sum((y - y.mean()) ** 2)) or 1e-9
    r2 = max(0.0, 1 - ss_res / ss_tot)

    if slope > 0.01:
        trend, rec = "rising", "buy_now"
    elif slope < -0.01:
        trend, rec = "falling", "wait"
    else:
        trend, rec = "stable", "buy_anytime"

    return {
        "trend": trend,
        "slope_per_day": round(float(slope), 4),
        "confidence": round(r2, 2),
        "recommendation": rec,
    }
