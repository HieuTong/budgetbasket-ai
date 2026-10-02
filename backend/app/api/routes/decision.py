from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.models import Product, Purchase
from app.db.session import get_db
from app.services.decision import make_product_decision


router = APIRouter(
    prefix="/decision",
    tags=["decision"],
)


@router.get("/{product_id}")
def get_product_decision(
    product_id: int,
    user_id: int | None = None,
    forecast_horizon_weeks: int = 4,
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

    purchases = []

    if user_id is not None:
        purchases = (
            db.query(Purchase)
            .filter(
                Purchase.user_id == user_id,
            )
            .all()
        )

    products = (
        db.query(Product)
        .filter(Product.unit_price > 0)
        .all()
    )

    result = make_product_decision(
        product=product,
        purchases=purchases,
        products=products,
        forecast_horizon_weeks=forecast_horizon_weeks,
    )

    response = {
        "product_id": product.id,
        "product_name": product.name,
        "decision": result.decision.value,
        "confidence": result.confidence,
        "reason": result.reason,
    }

    if result.price_probability is not None:
        response["price_probability"] = (
            result.price_probability.as_dict()
        )

    return response
