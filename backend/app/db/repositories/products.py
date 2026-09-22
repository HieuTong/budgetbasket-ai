from sqlalchemy.orm import Session

from app.db.models import Product


def list_products(db: Session) -> list[Product]:
    return db.query(Product).order_by(Product.id.asc()).all()


def get_product(db: Session, product_id: int) -> Product | None:
    return db.query(Product).filter(Product.id == product_id).first()
