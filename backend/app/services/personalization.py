from collections import Counter
from datetime import datetime

from app.db.models import Product, Purchase


def personalized_utility(
    product: Product,
    purchases: list[Purchase],
    now: datetime | None = None,
) -> float:
    """Return an explainable 0-1 preference score from purchase behavior."""
    if not purchases:
        return 0.5

    now = now or datetime.utcnow()
    product_purchases = [p for p in purchases if p.product_id == product.id]

    if product_purchases:
        frequency = min(len(product_purchases) / len(purchases) * 4.0, 1.0)
        latest = max(
            (p.purchased_at for p in product_purchases if p.purchased_at),
            default=now,
        )
        age_days = max((now - latest).total_seconds() / 86400.0, 0.0)
        recency = max(0.0, 1.0 - age_days / 90.0)

        avg_quantity = sum(p.quantity or 0.0 for p in product_purchases) / len(product_purchases)
        quantity_fit = min(avg_quantity / 3.0, 1.0)

        score = 0.50 * frequency + 0.35 * recency + 0.15 * quantity_fit
        return round(max(0.0, min(score, 1.0)), 4)

    category_counts = Counter(
        purchase.product.category
        for purchase in purchases
        if purchase.product is not None and purchase.product.category
    )
    total_categories = sum(category_counts.values())
    if product.category and total_categories:
        category_affinity = min(category_counts[product.category] / total_categories * 2.0, 1.0)
        return round(0.15 + 0.20 * category_affinity, 4)

    return 0.1


def build_basket_candidates(
    products: list[Product],
    purchases: list[Purchase],
) -> list[dict]:
    return [
        {"product": product, "utility": personalized_utility(product, purchases)}
        for product in products
    ]
