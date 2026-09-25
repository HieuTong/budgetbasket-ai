from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.models import PriceObservation, Product
from app.db.session import get_db
from app.services.price_intelligence import build_market_price_snapshot


router = APIRouter(
    prefix="/price-intelligence",
    tags=["price-intelligence"],
)


@router.get("/{product_id}")
def get_market_price_snapshot(
    product_id: int,
    db: Session = Depends(get_db),
):
    product = (
        db.query(Product)
        .filter(Product.id == product_id)
        .first()
    )

    if product is None:
        raise HTTPException(
            status_code=404,
            detail="Product not found",
        )

    observations = (
        db.query(PriceObservation)
        .filter(PriceObservation.product_id == product_id)
        .all()
    )

    snapshot = build_market_price_snapshot(
        product=product,
        observations=observations,
    )

    return {
        "product_id": snapshot.product_id,
        "product_name": snapshot.product_name,
        "observed_price": snapshot.observed_price,
        "retail_price": snapshot.retail_price,
        "is_special": snapshot.is_special,
        "observation_count": snapshot.observation_count,
        "location_count": snapshot.location_count,
        "observed_at": snapshot.observed_at,
    }