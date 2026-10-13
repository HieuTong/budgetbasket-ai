import logging
import os

from sqlalchemy.orm import Session

from app.db.repositories.prices import get_latest_prices_for_products
from app.db.repositories.products import get_products_by_ids_ordered, list_products
from app.services.grocery_ranking import rerank_grocery_products

logger = logging.getLogger(__name__)


def list_catalog(
    db: Session,
    category: str | None = None,
    search: str | None = None,
    limit: int | None = None,
    opensearch_client=None,
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
        from opensearchpy.exceptions import (
            ConnectionError as OpenSearchConnectionError,
            ConnectionTimeout,
            TransportError,
        )

        from app.services.opensearch_catalog import search_product_ids

        # Retrieve a wider candidate pool so intent reranking can promote
        # relevant products that would otherwise fall outside the requested top-k.
        requested_limit = limit
        candidate_limit = max(limit * 4, 20) if limit is not None else 100

        try:
            product_ids = search_product_ids(
                search=search,
                category=category,
                limit=candidate_limit,
                client=opensearch_client,
            )
        except (OpenSearchConnectionError, ConnectionTimeout) as exc:
            logger.warning(
                "OpenSearch product search is unavailable; "
                "falling back to PostgreSQL: %s",
                exc,
            )
            products = list_products(
                db,
                category=category,
                search=search,
                limit=limit,
            )
        except TransportError as exc:
            # Do not hide mapping, index-name, authentication, or query errors.
            # Fall back only for transient timeout, overload, or server failures.
            if getattr(exc, "status_code", None) not in {
                408,
                429,
                500,
                502,
                503,
                504,
            }:
                raise

            logger.warning(
                "OpenSearch product search returned transient HTTP status %s; "
                "falling back to PostgreSQL",
                getattr(exc, "status_code", None),
            )
            products = list_products(
                db,
                category=category,
                search=search,
                limit=limit,
            )
        else:
            products = get_products_by_ids_ordered(db, product_ids)
            if search:
                products = rerank_grocery_products(products, search)
            if requested_limit is not None:
                products = products[:requested_limit]

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