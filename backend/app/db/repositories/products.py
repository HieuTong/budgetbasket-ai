from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.db.models import Product


def list_products(
    db: Session,
    category: str | None = None,
    search: str | None = None,
    limit: int | None = None,
    priced_only: bool = False,
) -> list[Product]:
    query = db.query(Product)

    if category:
        query = query.filter(
            Product.category == category
        )

    if search:
        pattern = f"%{search.strip()}%"

        query = query.filter(
            or_(
                Product.name.ilike(pattern),
                Product.brand.ilike(pattern),
                Product.category.ilike(pattern),
                Product.sub_category.ilike(pattern),
                Product.product_group.ilike(pattern),
            )
        )

    if priced_only:
        query = query.filter(
            Product.unit_price > 0
        )

    query = query.order_by(Product.id.asc())

    if limit is not None:
        query = query.limit(limit)

    return query.all()


def get_product(
    db: Session,
    product_id: int,
) -> Product | None:
    return (
        db.query(Product)
        .filter(Product.id == product_id)
        .first()
    )

def list_basket_products(
    db: Session,
) -> list[tuple[int, str, float, str | None, str | None]]:
    return db.execute(
        select(
            Product.id,
            Product.name,
            Product.unit_price,
            Product.category,
            Product.sub_category,
        )
        .where(Product.unit_price > 0)
        .order_by(Product.id.asc())
    ).all()
