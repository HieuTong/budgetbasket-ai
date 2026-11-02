from sqlalchemy.orm import Session, selectinload

from app.db.models import Product, Purchase


def get_user_purchases(db: Session, user_id: int) -> list[Purchase]:
    # selectinload fetches every purchase's product in ONE extra query
    # ("WHERE id IN (...)"). Without it, reading purchase.product later
    # triggers a separate query per product: the N+1 problem, which made
    # building a basket take ~40 s on the live server.
    return (
        db.query(Purchase)
        .options(selectinload(Purchase.product))
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
