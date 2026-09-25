from __future__ import annotations

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.db.models import DBProduct
from app.db.models import Product as DBProduct
from app.db.models import Purchase
from app.ml.similarity import Product as SimilarityProduct
from app.ml.similarity import SimilarityIndex
from app.ml.similarity import select_representatives
from app.services.personalization import personalized_utility


def _transaction_counts(
    products: list[DBProduct],
    purchases: list[Purchase],
) -> dict[int, int]:
    """Count observed purchases for each product SKU."""
    counts: dict[int, int] = {}

    for purchase in purchases:
        if purchase.product_id is None:
            continue

        counts[purchase.product_id] = (
            counts.get(purchase.product_id, 0) + 1
        )

    return {
        product.id: counts.get(product.id, 0)
        for product in products
    }


def _to_similarity_product(
    product: DBProduct,
) -> SimilarityProduct:
    """Convert a database product into the ML-layer representation."""
    return SimilarityProduct(
        id=product.id,
        name=product.name,
        category=product.category or "",
        unit_price=product.unit_price,
        brand=product.brand or "",
        sub_category=product.sub_category or "",
        product_group=product.product_group or "",
        package_size=product.package_size or "",
        nutrition_tags=product.nutrition_tags or "",
    )


def build_similarity_index(
    products: list[DBProduct],
) -> SimilarityIndex:
    """
    Build a TF-IDF similarity index from database products.

    The ML layer remains independent from SQLAlchemy models.
    """
    similarity_products = [
        _to_similarity_product(product)
        for product in products
    ]

    return SimilarityIndex(
        similarity_products,
    )


def find_similar_products(
    product: DBProduct,
    products: list[DBProduct],
    purchases: list[Purchase],
    top_k: int = 5,
) -> list[tuple[DBProduct, float]]:
    """
    Find practical product alternatives.

    Source SKUs are grouped into practical product groups first.
    The SKU with the most observed transactions represents each group.

    The database records are not modified or deleted.
    """
    transaction_counts = _transaction_counts(
        products,
        purchases,
    )

    representatives = select_representatives(
        products,
        transaction_counts,
    )

    representative_ids = {
        item.id
        for item in representatives
    }

    if product.id not in representative_ids:
        representatives.append(product)

    similarity_products = [
        _to_similarity_product(item)
        for item in representatives
    ]

    index = SimilarityIndex(
        similarity_products,
    )

    results = index.recommend_similar(
        product_id=product.id,
        top_k=top_k,
    )

    products_by_id = {
        item.id: item
        for item in products
    }

    return [
        (
            products_by_id[similar_product.id],
            similarity,
        )
        for similar_product, similarity in results
        if similar_product.id in products_by_id
    ]


def find_cheaper_substitutes(
    product: DBProduct,
    products: list[DBProduct],
    purchases: list[Purchase],
    top_k: int = 5,
) -> list[dict]:
    """
    Find cheaper alternatives and enrich them with user preference.

    Products without a valid price cannot be evaluated as cheaper
    substitutes and are therefore excluded.

    Ranking signals:
    - semantic similarity
    - price savings
    - user's historical preference
    """

    if product.unit_price <= 0:
        return []

    priced_products = [
        candidate
        for candidate in products
        if candidate.unit_price > 0
    ]

    if not any(
        candidate.id == product.id
        for candidate in priced_products
    ):
        return []

    transaction_counts = _transaction_counts(
        priced_products,
        purchases,
    )

    representatives = select_representatives(
        priced_products,
        transaction_counts,
    )

    representative_ids = {
        item.id
        for item in representatives
    }

    if product.id not in representative_ids:
        representatives.append(product)

    index = build_similarity_index(
        representatives,
    )

    results = index.cheaper_substitutes(
        product_id=product.id,
        top_k=max(
            top_k * 3,
            10,
        ),
    )

    products_by_id = {
        item.id: item
        for item in representatives
    }

    enriched = []

    for similar_product, similarity in results:
        candidate = products_by_id.get(
            similar_product.id,
        )

        if candidate is None:
            continue

        if candidate.unit_price >= product.unit_price:
            continue

        savings = (
            product.unit_price
            - candidate.unit_price
        )

        savings_percent = (
            savings
            / product.unit_price
            * 100.0
        )

        preference = personalized_utility(
            candidate,
            purchases,
        )

        score = (
            0.60 * similarity
            + 0.20 * min(
                savings_percent / 50.0,
                1.0,
            )
            + 0.20 * preference
        )

        enriched.append(
            {
                "product": candidate,
                "similarity": round(
                    similarity,
                    4,
                ),
                "savings": round(
                    savings,
                    2,
                ),
                "savings_percent": round(
                    savings_percent,
                    2,
                ),
                "preference": round(
                    preference,
                    4,
                ),
                "score": round(
                    score,
                    4,
                ),
            }
        )

    enriched.sort(
        key=lambda item: item["score"],
        reverse=True,
    )

    return enriched[:top_k]