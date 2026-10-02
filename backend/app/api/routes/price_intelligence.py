from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.models import PriceObservation, Product, Purchase
from app.db.session import get_db
from app.ml.forecasting import PricePoint, price_trend
from app.services.price_intelligence import (
    build_market_price_snapshot,
    build_product_price_history,
)


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
        .filter(
            PriceObservation.product_id == product_id
        )
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


@router.get("/{product_id}/history")
def get_product_price_history(
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

    purchases = (
        db.query(Purchase)
        .filter(
            Purchase.product_id == product_id,
            Purchase.source == "dunnhumby_complete_journey",
        )
        .order_by(Purchase.purchased_at)
        .all()
    )

    history = build_product_price_history(
        product=product,
        purchases=purchases,
    )

    return {
        "product_id": history.product_id,
        "product_name": history.product_name,
        "observation_count": history.observation_count,
        "points": [
            {
                "date": point.date.isoformat(),
                "unit_price": point.unit_price,
                "transaction_count": point.transaction_count,
            }
            for point in history.points
        ],
    }


@router.get("/{product_id}/forecast")
def get_product_price_forecast(
    product_id: int,
    db: Session = Depends(get_db),
):
    """
    Forecast the product's near-term price movement.

    Uses Dunnhumby transaction history as the temporal price source.
    The model regularizes irregular transaction observations into
    weekly prices before fitting a linear trend.
    """

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

    purchases = (
        db.query(Purchase)
        .filter(
            Purchase.product_id == product_id,
            Purchase.source == "dunnhumby_complete_journey",
        )
        .order_by(Purchase.purchased_at)
        .all()
    )

    history = build_product_price_history(
        product=product,
        purchases=purchases,
    )

    price_points = [
        PricePoint(
            date=point.date,
            unit_price=point.unit_price,
            transaction_count=point.transaction_count,
        )
        for point in history.points
    ]

    forecast = price_trend(
        history=price_points,
        forecast_horizon_weeks=4,
    )

    return {
        "product_id": product.id,
        "product_name": product.name,
        "forecast": forecast,
    }

