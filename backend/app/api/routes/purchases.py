from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.repositories.purchases import get_user_purchases
from app.db.session import get_db

router = APIRouter()


@router.get("/{user_id}")
def get_purchases(user_id: int, db: Session = Depends(get_db)):
    rows = get_user_purchases(db, user_id)
    return [
        {
            "product_id": row.product_id,
            "name": row.product.name if row.product else None,
            "category": row.product.category if row.product else None,
            "unit_price": row.product.unit_price if row.product else None,
            "quantity": row.quantity,
            "purchased_at": row.purchased_at,
        }
        for row in rows
    ]
