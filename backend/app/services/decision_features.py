from __future__ import annotations

from dataclasses import dataclass
from statistics import mean, pstdev

from app.ml.forecasting import PricePoint


@dataclass(frozen=True)
class PriceFeatures:
    """Features describing recent price behaviour."""

    current_price: float
    change_1_week: float
    change_4_week: float
    mean_price: float
    volatility: float
    trend_per_week: float
    forecast_change_percent: float
    forecast_confidence: float
    observation_count: int


def _safe_change(
    current: float,
    previous: float,
) -> float:
    if previous <= 0:
        return 0.0

    return (current - previous) / previous


def build_price_features(
    history: list[PricePoint],
    trend_per_week: float = 0.0,
    forecast_change_percent: float = 0.0,
    forecast_confidence: float = 0.0,
) -> PriceFeatures | None:
    """
    Build a compact feature vector from historical price observations.

    The history is expected to be chronologically ordered.
    """

    if not history:
        return None

    prices = [
        point.unit_price
        for point in history
        if point.unit_price > 0
    ]

    if not prices:
        return None

    current_price = prices[-1]

    change_1_week = 0.0

    if len(prices) >= 2:
        change_1_week = _safe_change(
            current_price,
            prices[-2],
        )

    change_4_week = 0.0

    if len(prices) >= 5:
        change_4_week = _safe_change(
            current_price,
            prices[-5],
        )

    mean_price = mean(prices)

    returns = []

    for previous, current in zip(
        prices,
        prices[1:],
    ):
        if previous > 0:
            returns.append(
                (current - previous) / previous
            )

    volatility = (
        pstdev(returns)
        if len(returns) >= 2
        else 0.0
    )

    return PriceFeatures(
        current_price=round(
            current_price,
            4,
        ),
        change_1_week=round(
            change_1_week,
            6,
        ),
        change_4_week=round(
            change_4_week,
            6,
        ),
        mean_price=round(
            mean_price,
            4,
        ),
        volatility=round(
            volatility,
            6,
        ),
        trend_per_week=round(
            trend_per_week,
            6,
        ),
        forecast_change_percent=round(
            forecast_change_percent / 100.0,
            6,
        ),
        forecast_confidence=round(
            forecast_confidence,
            6,
        ),
        observation_count=len(prices),
    )


def feature_vector(
    features: PriceFeatures,
) -> list[float]:
    """
    Convert PriceFeatures into the numeric representation
    used by the probabilistic model.
    """

    return [
        features.current_price,
        features.change_1_week,
        features.change_4_week,
        features.mean_price,
        features.volatility,
        features.trend_per_week,
        features.forecast_change_percent,
        features.forecast_confidence,
        float(features.observation_count),
    ]