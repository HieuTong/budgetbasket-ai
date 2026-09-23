from sqlalchemy.orm import Session

from app.db.models import Product


def list_products(db: Session, category: str | None = None) -> list[Product]:
    query = db.query(Product)
    if category:
        query = query.filter(Product.category == category)
    return query.order_by(Product.id.asc()).all()


def get_product(db: Session, product_id: int) -> Product | None:
    return db.query(Product).filter(Product.id == product_id).first()
