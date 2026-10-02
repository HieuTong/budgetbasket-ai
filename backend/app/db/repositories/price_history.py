from sqlalchemy.orm import Session

from app.db.models import PriceHistory


def get_product_price_history(db: Session, product_id: int) -> list[PriceHistory]:
    return (
        db.query(PriceHistory)
        .filter(PriceHistory.product_id == product_id)
        .order_by(PriceHistory.recorded_at.asc())
        .all()
    )
