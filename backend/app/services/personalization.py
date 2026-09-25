from collections import Counter
from datetime import datetime

from app.db.models import Product, Purchase
from app.services.category_mapping import canonical_category


def _reference_date(
    purchases: list[Purchase],
    now: datetime | None,
) -> datetime:
    """Choose a meaningful reference date for recency calculations."""
    purchase_dates = [
        purchase.purchased_at
        for purchase in purchases
        if purchase.purchased_at is not None
    ]

    if not purchase_dates:
        return now or datetime.utcnow()

    return max(purchase_dates)


def personalized_utility(
    product: Product,
    purchases: list[Purchase],
    now: datetime | None = None,
) -> float:
    """
    Return an explainable 0-1 preference score from purchase behavior.

    Signals:
    - exact product frequency
    - exact product recency
    - typical purchase quantity
    - canonical category affinity

    The score represents user preference, not product quality.
    """
    if not purchases:
        return 0.5

    reference_date = _reference_date(purchases, now)

    product_purchases = [
        purchase
        for purchase in purchases
        if purchase.product_id == product.id
    ]

    # Exact product history.
    if product_purchases:
        frequency = min(
            len(product_purchases) / len(purchases) * 4.0,
            1.0,
        )

        latest = max(
            (
                purchase.purchased_at
                for purchase in product_purchases
                if purchase.purchased_at is not None
            ),
            default=reference_date,
        )

        age_days = max(
            (reference_date - latest).total_seconds() / 86400.0,
            0.0,
        )

        recency = max(
            0.0,
            1.0 - age_days / 90.0,
        )

        average_quantity = (
            sum(purchase.quantity or 0.0 for purchase in product_purchases)
            / len(product_purchases)
        )

        quantity_fit = min(
            average_quantity / 3.0,
            1.0,
        )

        score = (
            0.50 * frequency
            + 0.35 * recency
            + 0.15 * quantity_fit
        )

        return round(
            max(0.0, min(score, 1.0)),
            4,
        )

    # Category-level fallback.
    purchase_category_counts = Counter()

    for purchase in purchases:
        if purchase.product is None:
            continue

        category = canonical_category(
            category=purchase.product.category,
            sub_category=purchase.product.sub_category,
            product_name=purchase.product.name,
        )

        if category:
            purchase_category_counts[category] += 1

    candidate_category = canonical_category(
        category=product.category,
        sub_category=product.sub_category,
        product_name=product.name,
    )

    total_category_purchases = sum(
        purchase_category_counts.values()
    )

    if candidate_category and total_category_purchases:
        category_count = purchase_category_counts.get(
            candidate_category,
            0,
        )

        category_share = (
            category_count / total_category_purchases
        )

        category_affinity = min(
            category_share * 2.0,
            1.0,
        )

        score = 0.15 + 0.40 * category_affinity

        return round(
            max(0.0, min(score, 1.0)),
            4,
        )

    return 0.1


def build_basket_candidates(
    products: list[Product],
    purchases: list[Purchase],
) -> list[dict]:
    """Build optimizer candidates with personalized utility scores."""
    return [
        {
            "product": product,
            "utility": personalized_utility(
                product,
                purchases,
            ),
        }
        for product in products
    ]
