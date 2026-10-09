import os

from sqlalchemy.orm import Session

from app.db.repositories.prices import get_latest_prices_for_products
from app.db.repositories.products import get_products_by_ids_ordered, list_products


def list_catalog(
    db: Session,
    category: str | None = None,
    search: str | None = None,
    limit: int | None = None,
) -> list[dict]:
    backend = os.getenv("PRODUCT_SEARCH_BACKEND", "legacy").strip().lower()
    if backend == "legacy":
        products = list_products(
            db,
            category=category,
            search=search,
            limit=limit,
        )
    elif backend == "opensearch":
        from app.services.opensearch_catalog import search_product_ids

        product_ids = search_product_ids(
            search=search,
            category=category,
            limit=limit if limit is not None else 100,
        )
        products = get_products_by_ids_ordered(db, product_ids)
    else:
        raise RuntimeError(
            "Unsupported PRODUCT_SEARCH_BACKEND. Use 'legacy' or 'opensearch'."
        )

    latest_prices = get_latest_prices_for_products(
        db,
        [product.id for product in products],
    )

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
                "price": (
                    float(latest.price)
                    if latest
                    else product.unit_price
                ),
                "price_observed_at": (
                    latest.observed_at
                    if latest
                    else None
                ),
                "price_source": (
                    latest.source
                    if latest
                    else "product_seed"
                ),
            }
        )

    return catalog
