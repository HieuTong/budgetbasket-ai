"""
Lightweight price forecasting for DecisionOS.

The MVP uses linear regression over a regular weekly price series.

Pipeline:
    transaction-level prices
        -> weekly median prices
        -> linear trend
        -> forecast price
        -> buy-now vs wait signal

Why linear regression?
- Simple to explain and debug.
- Very small dependency footprint.
- Appropriate as a baseline for a portfolio MVP.
- Gives us an explicit baseline before introducing heavier models.

Upgrade path:
- Seasonal models when products have enough history.
- XGBoost/LightGBM with lag and rolling features.
- Prophet or other time-series models when there is sufficient
  per-product history and seasonality to justify the complexity.

Important:
Dunnhumby's dates are a normalized timeline used by this project.
They should not be interpreted as real-world calendar dates.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta

import numpy as np


@dataclass
class PricePoint:
    """A regularized price observation used by the forecasting model."""

    date: date
    unit_price: float
    transaction_count: int = 1


def aggregate_weekly_prices(
    history: list[PricePoint],
) -> list[PricePoint]:
    """
    Aggregate irregular transaction observations into weekly median prices.

    A week is anchored to the first observed date in the supplied history.
    Median price is used to reduce the effect of unusual transaction prices.
    """

    if not history:
        return []

    history = sorted(
        history,
        key=lambda point: point.date,
    )

    start_date = history[0].date

    weekly_prices: dict[int, list[float]] = {}
    weekly_counts: dict[int, int] = {}

    for point in history:
        week_index = (
            point.date - start_date
        ).days // 7

        weekly_prices.setdefault(
            week_index,
            [],
        ).append(point.unit_price)

        weekly_counts[week_index] = (
            weekly_counts.get(week_index, 0)
            + point.transaction_count
        )

    weekly_history = []

    for week_index in sorted(weekly_prices):
        prices = weekly_prices[week_index]

        weekly_history.append(
            PricePoint(
                date=start_date + timedelta(
                    days=week_index * 7,
                ),
                unit_price=float(np.median(prices)),
                transaction_count=weekly_counts[week_index],
            )
        )

    return weekly_history


def _decision_from_forecast(
    current_price: float,
    forecast_price: float,
) -> tuple[str, str]:
    """
    Convert forecast movement into an explainable decision signal.

    The decision is based on the relative difference between the current
    price and the forecast price rather than the regression slope alone.

    A 5% threshold prevents small model fluctuations from producing
    strong buy/wait recommendations.
    """

    if current_price <= 0:
        return "unknown", "insufficient_data"

    relative_change = (
        (forecast_price - current_price)
        / current_price
    )

    if relative_change >= 0.05:
        return "rising", "buy_now"

    if relative_change <= -0.05:
        return "falling", "wait"

    return "stable", "buy_anytime"


def price_trend(
    history: list[PricePoint],
    forecast_horizon_weeks: int = 4,
) -> dict:
    """
    Forecast a product's near-term price movement.

    Steps:
        1. Sort observations chronologically.
        2. Aggregate irregular observations into weekly medians.
        3. Fit linear regression over weekly prices.
        4. Forecast the price `forecast_horizon_weeks` into the future.
        5. Compare the forecast with the current price.
        6. Produce an explainable buy/wait signal.

    Returns a dictionary for easy use by the API and agent layers.
    """

    if forecast_horizon_weeks <= 0:
        raise ValueError(
            "forecast_horizon_weeks must be positive"
        )

    if len(history) < 2:
        return {
            "trend": "unknown",
            "slope_per_week": 0.0,
            "confidence": 0.0,
            "current_price": (
                round(history[-1].unit_price, 2)
                if history
                else None
            ),
            "forecast_price": None,
            "forecast_horizon_weeks": forecast_horizon_weeks,
            "forecast_change_percent": None,
            "recommendation": "insufficient_data",
            "observation_count": len(history),
        }

    weekly_history = aggregate_weekly_prices(history)

    if len(weekly_history) < 2:
        current_price = weekly_history[-1].unit_price

        return {
            "trend": "unknown",
            "slope_per_week": 0.0,
            "confidence": 0.0,
            "current_price": round(current_price, 2),
            "forecast_price": None,
            "forecast_horizon_weeks": forecast_horizon_weeks,
            "forecast_change_percent": None,
            "recommendation": "insufficient_data",
            "observation_count": len(history),
        }

    x = np.arange(
        len(weekly_history),
        dtype=float,
    )

    y = np.array(
        [
            point.unit_price
            for point in weekly_history
        ],
        dtype=float,
    )

    slope, intercept = np.polyfit(
        x,
        y,
        1,
    )

    predicted = (
        slope * x
        + intercept
    )

    residuals = y - predicted

    ss_res = float(
        np.sum(residuals**2)
    )

    ss_tot = float(
        np.sum((y - y.mean()) ** 2)
    )

    if ss_tot > 0:
        r2 = max(
            0.0,
            min(
                1.0,
                1.0 - ss_res / ss_tot,
            ),
        )
    else:
        r2 = 0.0

    current_price = float(
        weekly_history[-1].unit_price
    )

    future_x = (
        len(weekly_history)
        - 1
        + forecast_horizon_weeks
    )

    forecast_price = float(
        slope * future_x
        + intercept
    )

    # Prices should never be negative.
    forecast_price = max(
        0.0,
        forecast_price,
    )

    forecast_change_percent = (
        (
            forecast_price - current_price
        )
        / current_price
        * 100.0
        if current_price > 0
        else None
    )

    trend, recommendation = _decision_from_forecast(
        current_price=current_price,
        forecast_price=forecast_price,
    )

    return {
        "trend": trend,
        "slope_per_week": round(
            float(slope),
            4,
        ),
        "confidence": round(
            r2,
            2,
        ),
        "current_price": round(
            current_price,
            2,
        ),
        "forecast_price": round(
            forecast_price,
            2,
        ),
        "forecast_horizon_weeks": forecast_horizon_weeks,
        "forecast_change_percent": round(
            forecast_change_percent,
            2,
        ) if forecast_change_percent is not None else None,
        "recommendation": recommendation,
        "observation_count": len(history),
    }
