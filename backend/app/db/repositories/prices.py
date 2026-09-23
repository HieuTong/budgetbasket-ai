from datetime import datetime

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
        .order_by(PriceObservation.observed_at.desc())
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
        .order_by(PriceObservation.observed_at.desc())
        .first()
    )


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
