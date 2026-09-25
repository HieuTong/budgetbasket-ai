from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.models import Purchase
from app.db.session import get_db
from app.services.purchase_profile import build_purchase_profile


router = APIRouter(
    prefix="/purchase-profile",
    tags=["purchase-intelligence"],
)


@router.get("/{user_id}")
def get_purchase_profile(
    user_id: int,
    db: Session = Depends(get_db),
):
    purchases = (
        db.query(Purchase)
        .filter(Purchase.user_id == user_id)
        .all()
    )

    if not purchases:
        raise HTTPException(
            status_code=404,
            detail="User has no purchase history",
        )

    profile = build_purchase_profile(
        user_id=user_id,
        purchases=purchases,
    )

    return {
        "user_id": profile.user_id,
        "analysis_period_days": profile.analysis_period_days,
        "transaction_count": profile.transaction_count,
        "unique_products": profile.unique_products,
        "unique_categories": profile.unique_categories,
        "average_quantity": profile.average_quantity,
        "purchases_per_month": profile.purchases_per_month,
        "recent_purchase_count": profile.recent_purchase_count,
        "category_frequency": profile.category_frequency,
        "product_frequency": profile.product_frequency,
    }