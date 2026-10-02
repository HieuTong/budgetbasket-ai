from sqlalchemy.orm import Session

from app.db.models import Product, Purchase


def get_user_purchases(db: Session, user_id: int) -> list[Purchase]:
    return (
        db.query(Purchase)
        .filter(Purchase.user_id == user_id)
        .order_by(Purchase.purchased_at.desc())
        .all()
    )


def get_user_purchase_summary(db: Session, user_id: int) -> list[dict]:
    rows = (
        db.query(
            Purchase.product_id,
            Product.name,
            Product.category,
            Product.unit_price,
            Purchase.quantity,
        )
        .join(Product, Product.id == Purchase.product_id)
        .filter(Purchase.user_id == user_id)
        .all()
    )
    return [
        {
            "product_id": product_id,
            "name": name,
            "category": category,
            "unit_price": unit_price,
            "quantity": quantity,
        }
        for product_id, name, category, unit_price, quantity in rows
    ]
