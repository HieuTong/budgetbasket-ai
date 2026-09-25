from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from app.db.models import PriceObservation, Product


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

    The current dataset is a single-date market snapshot, so this
    function intentionally does not calculate historical trends,
    price changes, or forecasts.
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