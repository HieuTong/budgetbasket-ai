from datetime import datetime

from app.db.models import Product, Purchase
from app.services.decision_dataset import (
    DecisionDatasetBuilder,
)
from app.services.decision_model import (
    DECREASE,
    INCREASE,
    STABLE,
)


def _product(
    product_id: int,
    name: str = "Test Product",
) -> Product:
    return Product(
        id=product_id,
        name=name,
        unit_price=2.00,
    )


def _purchase(
    product_id: int,
    purchased_at: datetime,
    sales_value: float = 2.00,
    quantity: float = 1.0,
) -> Purchase:
    return Purchase(
        product_id=product_id,
        source="dunnhumby_complete_journey",
        purchased_at=purchased_at,
        sales_value=sales_value,
        quantity=quantity,
        retail_discount=0.0,
        coupon_match_discount=0.0,
    )


def _weekly_purchases(
    product_id: int,
    prices: list[float],
) -> list[Purchase]:
    from datetime import timedelta

    start = datetime(2026, 1, 5)

    return [
        _purchase(
            product_id=product_id,
            purchased_at=(
                start
                + timedelta(weeks=index)
            ),
            sales_value=price,
        )
        for index, price in enumerate(prices)
    ]


def test_builder_creates_dataset():
    product = _product(1)

    purchases = _weekly_purchases(
        1,
        [
            2.00,
            2.00,
            2.00,
            2.00,
            2.00,
            2.10,
            2.20,
            2.30,
            2.40,
            2.50,
        ],
    )

    builder = DecisionDatasetBuilder(
        lookback_weeks=4,
        forecast_horizon_weeks=4,
        min_weekly_observations=9,
    )

    dataset = builder.build(
        products=[product],
        purchases=purchases,
    )

    assert dataset.sample_count > 0
    assert len(dataset.targets) == dataset.sample_count
    assert len(dataset.product_ids) == dataset.sample_count
    assert len(dataset.current_dates) == dataset.sample_count
    assert len(dataset.future_dates) == dataset.sample_count


def test_builder_skips_products_without_enough_history():
    product = _product(1)

    purchases = _weekly_purchases(
        1,
        [
            2.00,
            2.00,
            2.00,
            2.00,
        ],
    )

    builder = DecisionDatasetBuilder(
        min_weekly_observations=9,
    )

    dataset = builder.build(
        products=[product],
        purchases=purchases,
    )

    assert dataset.sample_count == 0


def test_builder_ignores_non_dunnhumby_purchases():
    product = _product(1)

    purchases = _weekly_purchases(
        1,
        [
            2.00,
            2.00,
            2.00,
            2.00,
            2.00,
            2.10,
            2.20,
            2.30,
            2.40,
            2.50,
        ],
    )

    purchases.append(
        Purchase(
            product_id=1,
            source="other_source",
            purchased_at=datetime(2026, 6, 1),
            sales_value=100.0,
            quantity=1.0,
        )
    )

    builder = DecisionDatasetBuilder(
        min_weekly_observations=9,
    )

    dataset = builder.build(
        products=[product],
        purchases=purchases,
    )

    assert dataset.sample_count > 0


def test_builder_skips_purchases_without_product_id():
    product = _product(1)

    purchases = _weekly_purchases(
        1,
        [
            2.00,
            2.00,
            2.00,
            2.00,
            2.00,
            2.10,
            2.20,
            2.30,
            2.40,
            2.50,
        ],
    )

    purchases.append(
        Purchase(
            product_id=None,
            source="dunnhumby_complete_journey",
            purchased_at=datetime(2026, 6, 1),
            sales_value=10.0,
            quantity=1.0,
        )
    )

    builder = DecisionDatasetBuilder(
        min_weekly_observations=9,
    )

    dataset = builder.build(
        products=[product],
        purchases=purchases,
    )

    assert dataset.sample_count > 0


def test_dataset_keeps_product_and_date_alignment():
    product = _product(42)

    purchases = _weekly_purchases(
        42,
        [
            2.00,
            2.00,
            2.00,
            2.00,
            2.00,
            2.00,
            2.10,
            2.20,
            2.30,
            2.40,
            2.50,
            2.60,
            2.70,
        ],
    )

    builder = DecisionDatasetBuilder(
        lookback_weeks=4,
        forecast_horizon_weeks=4,
        min_weekly_observations=9,
    )

    dataset = builder.build(
        products=[product],
        purchases=purchases,
    )

    assert dataset.sample_count > 0

    for index in range(dataset.sample_count):
        assert dataset.product_ids[index] == 42
        assert (
            dataset.current_dates[index]
            < dataset.future_dates[index]
        )

    assert set(dataset.targets).issubset(
        {
            INCREASE,
            STABLE,
            DECREASE,
        }
    )

