from datetime import datetime, timedelta

from app.ml.forecasting import PricePoint, price_trend


def test_forecast_requires_two_points():
    result = price_trend([PricePoint(price=3.50, recorded_at=datetime(2026, 1, 1))])

    assert result["trend"] == "unknown"
    assert result["recommendation"] == "insufficient_data"
    assert result["confidence"] == 0.0


def test_rising_prices_are_detected():
    start = datetime(2026, 1, 1)
    history = [
        PricePoint(price=3.00, recorded_at=start),
        PricePoint(price=3.50, recorded_at=start + timedelta(days=30)),
    ]

    result = price_trend(history)

    assert result["trend"] == "rising"
    assert result["recommendation"] == "buy_now"


def test_falling_prices_are_detected():
    start = datetime(2026, 1, 1)
    history = [
        PricePoint(price=4.00, recorded_at=start),
        PricePoint(price=3.50, recorded_at=start + timedelta(days=30)),
    ]

    result = price_trend(history)

    assert result["trend"] == "falling"
    assert result["recommendation"] == "wait"
