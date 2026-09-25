from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from statistics import median

from app.db.models import PriceObservation, Product, Purchase


DUNNHUMBY_SOURCE = "dunnhumby_complete_journey"


@dataclass
class MarketPriceSnapshot:
    product_id: int
    product_name: str
    observed_price: float | None
    retail_price: float | None
    is_special: bool
    observation_count: int
    location_count: int
    observed_at: str | None


@dataclass
class PricePoint:
    date: date
    unit_price: float
    transaction_count: int


@dataclass
class ProductPriceHistory:
    product_id: int
    product_name: str
    points: list[PricePoint]
    observation_count: int


def _to_float(value: Decimal | float | int | None) -> float | None:
    if value is None:
        return None

    return float(value)


def build_market_price_snapshot(
    product: Product,
    observations: list[PriceObservation],
) -> MarketPriceSnapshot:
    """
    Build a market-price snapshot for a product.

    The current Kaggle Australia Grocery dataset is a single-date
    market snapshot, so this function does not calculate historical
    trends or forecasts.
    """

    if not observations:
        return MarketPriceSnapshot(
            product_id=product.id,
            product_name=product.name,
            observed_price=None,
            retail_price=None,
            is_special=False,
            observation_count=0,
            location_count=0,
            observed_at=None,
        )

    latest = max(
        observations,
        key=lambda observation: observation.observed_at,
    )

    prices = [
        _to_float(observation.price)
        for observation in observations
        if observation.price is not None
    ]

    locations = {
        (
            observation.city,
            observation.state,
        )
        for observation in observations
        if observation.city or observation.state
    }

    return MarketPriceSnapshot(
        product_id=product.id,
        product_name=product.name,
        observed_price=round(
            sum(prices) / len(prices),
            2,
        ) if prices else None,
        retail_price=_to_float(latest.retail_price),
        is_special=any(
            observation.is_special
            for observation in observations
        ),
        observation_count=len(observations),
        location_count=len(locations),
        observed_at=(
            latest.observed_at.isoformat()
            if latest.observed_at
            else None
        ),
    )


def _dunnhumby_unit_price(purchase: Purchase) -> float | None:
    """
    Calculate the Dunnhumby loyalty-card unit price.

    Dunnhumby's transaction data stores discounts as negative values.

    Loyalty-card price:
        (sales_value - (retail_disc + coupon_match_disc)) / quantity

    coupon_disc is intentionally excluded because it represents a
    manufacturer coupon rather than the retailer's shelf price.
    """

    quantity = purchase.quantity or 0.0
    sales_value = _to_float(purchase.sales_value)

    if quantity <= 0 or sales_value is None:
        return None

    retail_discount = _to_float(
        purchase.retail_discount
    ) or 0.0

    coupon_match_discount = _to_float(
        purchase.coupon_match_discount
    ) or 0.0

    unit_price = (
        sales_value
        - (retail_discount + coupon_match_discount)
    ) / quantity

    if unit_price < 0:
        return None

    return round(unit_price, 4)


def build_product_price_history(
    product: Product,
    purchases: list[Purchase],
) -> ProductPriceHistory:
    """
    Build a daily product-price history from Dunnhumby transactions.

    Multiple transactions for the same product on the same normalized
    date are aggregated using the median unit price.
    """

    daily_prices: dict[date, list[float]] = {}

    relevant_purchases = [
        purchase
        for purchase in purchases
        if (
            purchase.product_id == product.id
            and purchase.source == DUNNHUMBY_SOURCE
            and purchase.purchased_at is not None
        )
    ]

    for purchase in relevant_purchases:
        unit_price = _dunnhumby_unit_price(purchase)

        if unit_price is None:
            continue

        purchase_date = purchase.purchased_at.date()

        daily_prices.setdefault(
            purchase_date,
            [],
        ).append(unit_price)

    points = [
        PricePoint(
            date=price_date,
            unit_price=round(
                median(prices),
                2,
            ),
            transaction_count=len(prices),
        )
        for price_date, prices in sorted(
            daily_prices.items()
        )
    ]

    return ProductPriceHistory(
        product_id=product.id,
        product_name=product.name,
        points=points,
        observation_count=sum(
            point.transaction_count
            for point in points
        ),
    )