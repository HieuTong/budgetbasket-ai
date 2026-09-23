from sqlalchemy.orm import Session

from app.db.repositories.prices import get_latest_prices_for_products
from app.db.repositories.products import list_products


def list_catalog(db: Session, category: str | None = None) -> list[dict]:
    products = list_products(db, category=category)
    latest_prices = get_latest_prices_for_products(db, [product.id for product in products])

    catalog = []
    for product in products:
        latest = latest_prices.get(product.id)
        catalog.append(
            {
                "product_id": product.id,
                "name": product.name,
                "brand": product.brand,
                "category": product.category,
                "sub_category": product.sub_category,
                "package_size": product.package_size,
                "unit": product.unit,
                "price": float(latest.price) if latest else product.unit_price,
                "price_observed_at": latest.observed_at if latest else None,
                "price_source": latest.source if latest else "product_seed",
            }
        )
    return catalog
