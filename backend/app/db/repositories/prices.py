from datetime import datetime

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.db.models import PriceObservation


def list_product_prices(
    db: Session,
    product_id: int,
    limit: int = 90,
) -> list[PriceObservation]:
    """Return the most recent observations for one product."""
    return (
        db.query(PriceObservation)
        .filter(PriceObservation.product_id == product_id)
        .order_by(PriceObservation.observed_at.desc(), PriceObservation.id.desc())
        .limit(limit)
        .all()
    )


def get_latest_product_price(
    db: Session,
    product_id: int,
) -> PriceObservation | None:
    return (
        db.query(PriceObservation)
        .filter(PriceObservation.product_id == product_id)
        .order_by(PriceObservation.observed_at.desc(), PriceObservation.id.desc())
        .first()
    )


def get_latest_prices_for_products(
    db: Session,
    product_ids: list[int],
) -> dict[int, PriceObservation]:
    """Fetch one latest observation per product in a single database query."""
    if not product_ids:
        return {}

    latest_at = (
        db.query(
            PriceObservation.product_id,
            func.max(PriceObservation.observed_at).label("max_observed_at"),
        )
        .filter(PriceObservation.product_id.in_(product_ids))
        .group_by(PriceObservation.product_id)
        .subquery()
    )

    rows = (
        db.query(PriceObservation)
        .join(
            latest_at,
            (PriceObservation.product_id == latest_at.c.product_id)
            & (PriceObservation.observed_at == latest_at.c.max_observed_at),
        )
        .all()
    )

    # The dataset normally has one observation per product/day. If two sources
    # share the same timestamp, keep the highest id as the deterministic latest row.
    latest: dict[int, PriceObservation] = {}
    for row in rows:
        current = latest.get(row.product_id)
        if current is None or row.id > current.id:
            latest[row.product_id] = row
    return latest


def create_price_observation(
    db: Session,
    *,
    product_id: int,
    price: float,
    observed_at: datetime,
    source: str,
    store_id: int | None = None,
    source_record_id: str | None = None,
    is_estimated: bool | None = None,
) -> PriceObservation:
    observation = PriceObservation(
        product_id=product_id,
        store_id=store_id,
        price=price,
        observed_at=observed_at,
        source=source,
        source_record_id=source_record_id,
        is_estimated=is_estimated,
    )
    db.add(observation)
    return observation
