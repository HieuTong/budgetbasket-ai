from datetime import date

from app.services.price_intelligence import (
    ProductPriceHistory,
    PricePoint,
    aggregate_weekly_price_history,
)


def test_aggregate_weekly_price_history_uses_median():
    history = ProductPriceHistory(
        product_id=70803,
        product_name="Test Product",
        points=[
            PricePoint(
                date=date(2026, 1, 5),
                unit_price=2.00,
                transaction_count=2,
            ),
            PricePoint(
                date=date(2026, 1, 6),
                unit_price=3.00,
                transaction_count=1,
            ),
            PricePoint(
                date=date(2026, 1, 7),
                unit_price=4.00,
                transaction_count=3,
            ),
        ],
        observation_count=6,
    )

    result = aggregate_weekly_price_history(
        history
    )

    assert len(result.points) == 1
    assert result.points[0].date == date(2026, 1, 5)
    assert result.points[0].unit_price == 3.00
    assert result.points[0].transaction_count == 6


def test_aggregate_weekly_price_history_separates_weeks():
    history = ProductPriceHistory(
        product_id=70803,
        product_name="Test Product",
        points=[
            PricePoint(
                date=date(2026, 1, 5),
                unit_price=2.00,
                transaction_count=1,
            ),
            PricePoint(
                date=date(2026, 1, 12),
                unit_price=3.00,
                transaction_count=2,
            ),
        ],
        observation_count=3,
    )

    result = aggregate_weekly_price_history(
        history
    )

    assert len(result.points) == 2
    assert result.points[0].unit_price == 2.00
    assert result.points[1].unit_price == 3.00
    assert result.points[0].transaction_count == 1
    assert result.points[1].transaction_count == 2


def test_aggregate_weekly_price_history_preserves_metadata():
    history = ProductPriceHistory(
        product_id=70803,
        product_name="Test Product",
        points=[
            PricePoint(
                date=date(2026, 1, 5),
                unit_price=2.00,
                transaction_count=1,
            ),
        ],
        observation_count=10,
    )

    result = aggregate_weekly_price_history(
        history
    )

    assert result.product_id == 70803
    assert result.product_name == "Test Product"
    assert result.observation_count == 10


def test_aggregate_weekly_price_history_handles_empty_history():
    history = ProductPriceHistory(
        product_id=70803,
        product_name="Test Product",
        points=[],
        observation_count=0,
    )

    result = aggregate_weekly_price_history(
        history
    )

    assert result.points == []
    assert result.observation_count == 0