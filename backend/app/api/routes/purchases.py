from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.models import Purchase
from app.db.session import get_db

router = APIRouter()


@router.get("/{user_id}")
def get_purchases(user_id: int, db: Session = Depends(get_db)):
    rows = db.query(Purchase).filter(Purchase.user_id == user_id).order_by(Purchase.purchased_at.desc()).all()
    return [{"product_id": r.product_id, "quantity": r.quantity, "purchased_at": r.purchased_at} for r in rows]
