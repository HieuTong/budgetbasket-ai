from datetime import date, timedelta

from app.ml.forecasting import PricePoint
from app.services.decision_features import (
    build_price_features,
    feature_vector,
)


def _history(
    prices: list[float],
) -> list[PricePoint]:
    start = date(2026, 1, 1)

    return [
        PricePoint(
            date=start + timedelta(weeks=index),
            unit_price=price,
            transaction_count=1,
        )
        for index, price in enumerate(prices)
    ]


def test_build_price_features():
    history = _history(
        [
            8.00,
            8.10,
            8.20,
            8.30,
            8.40,
            8.60,
        ]
    )

    features = build_price_features(
        history=history,
        trend_per_week=0.10,
        forecast_change_percent=8.0,
        forecast_confidence=0.70,
    )

    assert features is not None

    assert features.current_price == 8.60
    assert features.change_1_week == round(
        (8.60 - 8.40) / 8.40,
        6,
    )
    assert features.change_4_week == round(
        (8.60 - 8.10) / 8.10,
        6,
    )
    assert features.forecast_change_percent == 0.08
    assert features.forecast_confidence == 0.70
    assert features.observation_count == 6


def test_feature_vector_contains_nine_features():
    history = _history(
        [
            8.00,
            8.10,
            8.20,
            8.30,
            8.40,
        ]
    )

    features = build_price_features(
        history=history,
    )

    assert features is not None

    vector = feature_vector(features)

    assert len(vector) == 9
    assert vector[0] == 8.40
    assert vector[1] > 0
    assert vector[2] > 0


def test_empty_history_returns_none():
    result = build_price_features([])

    assert result is None


def test_zero_or_negative_prices_are_ignored():
    history = _history(
        [
            8.00,
            0.00,
            -1.00,
            8.50,
        ]
    )

    features = build_price_features(
        history=history,
    )

    assert features is not None
    assert features.current_price == 8.50
    assert features.observation_count == 2


def test_single_price_has_zero_changes_and_volatility():
    history = _history([8.50])

    features = build_price_features(
        history=history,
    )

    assert features is not None
    assert features.current_price == 8.50
    assert features.change_1_week == 0.0
    assert features.change_4_week == 0.0
    assert features.volatility == 0.0