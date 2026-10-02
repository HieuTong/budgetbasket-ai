from datetime import date, timedelta

from app.ml.forecasting import (
    PricePoint,
    aggregate_weekly_prices,
    price_trend,
)


def test_forecast_requires_two_points():
    result = price_trend(
        [
            PricePoint(
                date=date(2026, 1, 1),
                unit_price=3.50,
            )
        ]
    )

    assert result["trend"] == "unknown"
    assert result["recommendation"] == "insufficient_data"
    assert result["confidence"] == 0.0
    assert result["forecast_price"] is None


def test_weekly_prices_are_aggregated():
    start = date(2026, 1, 1)

    history = [
        PricePoint(
            date=start,
            unit_price=3.00,
        ),
        PricePoint(
            date=start + timedelta(days=2),
            unit_price=3.20,
        ),
        PricePoint(
            date=start + timedelta(days=7),
            unit_price=4.00,
        ),
    ]

    weekly = aggregate_weekly_prices(history)

    assert len(weekly) == 2
    assert weekly[0].unit_price == 3.10
    assert weekly[1].unit_price == 4.00


def test_rising_prices_are_detected():
    start = date(2026, 1, 1)

    history = [
        PricePoint(
            date=start,
            unit_price=3.00,
        ),
        PricePoint(
            date=start + timedelta(days=7),
            unit_price=3.50,
        ),
        PricePoint(
            date=start + timedelta(days=14),
            unit_price=4.00,
        ),
        PricePoint(
            date=start + timedelta(days=21),
            unit_price=4.50,
        ),
    ]

    result = price_trend(history)

    assert result["trend"] == "rising"
    assert result["recommendation"] == "buy_now"
    assert result["forecast_price"] > result["current_price"]
    assert result["forecast_change_percent"] > 5.0


def test_falling_prices_are_detected():
    start = date(2026, 1, 1)

    history = [
        PricePoint(
            date=start,
            unit_price=4.50,
        ),
        PricePoint(
            date=start + timedelta(days=7),
            unit_price=4.00,
        ),
        PricePoint(
            date=start + timedelta(days=14),
            unit_price=3.50,
        ),
        PricePoint(
            date=start + timedelta(days=21),
            unit_price=3.00,
        ),
    ]

    result = price_trend(history)

    assert result["trend"] == "falling"
    assert result["recommendation"] == "wait"
    assert result["forecast_price"] < result["current_price"]
    assert result["forecast_change_percent"] < -5.0


def test_small_forecast_change_is_stable():
    start = date(2026, 1, 1)

    history = [
        PricePoint(
            date=start,
            unit_price=3.00,
        ),
        PricePoint(
            date=start + timedelta(days=7),
            unit_price=3.01,
        ),
        PricePoint(
            date=start + timedelta(days=14),
            unit_price=3.02,
        ),
        PricePoint(
            date=start + timedelta(days=21),
            unit_price=3.03,
        ),
    ]

    result = price_trend(history)

    assert result["trend"] == "stable"
    assert result["recommendation"] == "buy_anytime"


def test_forecast_horizon_changes_forecast():
    start = date(2026, 1, 1)

    history = [
        PricePoint(
            date=start,
            unit_price=3.00,
        ),
        PricePoint(
            date=start + timedelta(days=7),
            unit_price=3.50,
        ),
        PricePoint(
            date=start + timedelta(days=14),
            unit_price=4.00,
        ),
    ]

    four_week = price_trend(
        history,
        forecast_horizon_weeks=4,
    )

    eight_week = price_trend(
        history,
        forecast_horizon_weeks=8,
    )

    assert (
        eight_week["forecast_price"]
        > four_week["forecast_price"]
    )
