from collections import defaultdict
from datetime import datetime

from app.db.models import Product, Purchase


def personalized_utility(
    product: Product,
    purchases: list[Purchase],
    now: datetime | None = None,
) -> float:
    """Return an explainable 0-1 preference score from purchase behavior.

    The first version intentionally uses deterministic behavioral signals:
    frequency, recency, and quantity preference. New users receive a neutral
    score so the optimizer can still operate without fabricated preferences.
    """
    if not purchases:
        return 0.5

    now = now or datetime.utcnow()
    product_purchases = [p for p in purchases if p.product_id == product.id]

    if not product_purchases:
        # A small category signal lets products in categories the user buys
        # remain viable without pretending the user prefers this exact item.
        category_product_ids = {
            p.product_id
            for p in purchases
            if p.product_id == product.id
        }
        return 0.2 if not category_product_ids else 0.5

    frequency = min(len(product_purchases) / max(len(purchases), 1) * 4.0, 1.0)
    latest = max(p.purchased_at for p in product_purchases)
    age_days = max((now - latest).total_seconds() / 86400.0, 0.0)
    recency = max(0.0, 1.0 - age_days / 90.0)

    avg_quantity = sum(p.quantity for p in product_purchases) / len(product_purchases)
    quantity_fit = min(avg_quantity / 3.0, 1.0)

    score = 0.50 * frequency + 0.35 * recency + 0.15 * quantity_fit
    return round(max(0.0, min(score, 1.0)), 4)


def build_basket_candidates(
    products: list[Product],
    purchases: list[Purchase],
) -> list[dict]:
    return [
        {
            "product": product,
            "utility": personalized_utility(product, purchases),
        }
        for product in products
    ]
