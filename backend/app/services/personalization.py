from collections import Counter
from dataclasses import dataclass
from datetime import datetime

from app.db.models import Product, Purchase
from app.services.category_mapping import canonical_category


@dataclass(frozen=True)
class PersonalizationProfile:
    purchase_count: int
    product_counts: dict[int, int]
    product_latest: dict[int, datetime]
    product_average_quantity: dict[int, float]
    category_counts: dict[str, int]


def build_personalization_profile(
    purchases: list[Purchase],
) -> PersonalizationProfile:
    product_counts = Counter()
    product_latest = {}
    product_quantities = {}
    category_counts = Counter()

    for purchase in purchases:
        if purchase.product_id is not None:
            product_counts[purchase.product_id] += 1

            if purchase.purchased_at is not None:
                current_latest = product_latest.get(
                    purchase.product_id
                )

                if (
                    current_latest is None
                    or purchase.purchased_at > current_latest
                ):
                    product_latest[purchase.product_id] = (
                        purchase.purchased_at
                    )

            quantity = purchase.quantity or 0.0

            if purchase.product_id not in product_quantities:
                product_quantities[purchase.product_id] = []

            product_quantities[purchase.product_id].append(
                quantity
            )

        if purchase.product is None:
            continue

        category = canonical_category(
            category=purchase.product.category,
            sub_category=purchase.product.sub_category,
            product_name=purchase.product.name,
        )

        if category:
            category_counts[category] += 1

    product_average_quantity = {
        product_id: sum(quantities) / len(quantities)
        for product_id, quantities in product_quantities.items()
    }

    return PersonalizationProfile(
        purchase_count=len(purchases),
        product_counts=dict(product_counts),
        product_latest=product_latest,
        product_average_quantity=product_average_quantity,
        category_counts=dict(category_counts),
    )


def _reference_date(
    purchases: list[Purchase],
    now: datetime | None,
) -> datetime:
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
    if not purchases:
        return 0.5

    profile = build_personalization_profile(purchases)

    return personalized_utility_from_profile(
        product,
        profile,
        _reference_date(purchases, now),
    )


def personalized_utility_from_profile(
    product: Product,
    profile: PersonalizationProfile,
    reference_date: datetime,
) -> float:
    if profile.purchase_count == 0:
        return 0.5

    product_count = profile.product_counts.get(
        product.id,
        0,
    )

    if product_count:
        frequency = min(
            product_count / profile.purchase_count * 4.0,
            1.0,
        )

        latest = profile.product_latest.get(
            product.id,
            reference_date,
        )

        age_days = max(
            (reference_date - latest).total_seconds() / 86400.0,
            0.0,
        )

        recency = max(
            0.0,
            1.0 - age_days / 90.0,
        )

        average_quantity = profile.product_average_quantity.get(
            product.id,
            0.0,
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

    candidate_category = canonical_category(
        category=product.category,
        sub_category=product.sub_category,
        product_name=product.name,
    )

    total_category_purchases = sum(
        profile.category_counts.values()
    )

    if candidate_category and total_category_purchases:
        category_count = profile.category_counts.get(
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


def personalized_utility_from_fields(
    product_id: int,
    category: str | None,
    sub_category: str | None,
    product_name: str,
    profile: PersonalizationProfile,
    reference_date: datetime,
) -> float:
    if profile.purchase_count == 0:
        return 0.5

    product_count = profile.product_counts.get(
        product_id,
        0,
    )

    if product_count:
        frequency = min(
            product_count / profile.purchase_count * 4.0,
            1.0,
        )

        latest = profile.product_latest.get(
            product_id,
            reference_date,
        )

        age_days = max(
            (reference_date - latest).total_seconds() / 86400.0,
            0.0,
        )

        recency = max(
            0.0,
            1.0 - age_days / 90.0,
        )

        average_quantity = profile.product_average_quantity.get(
            product_id,
            0.0,
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

    candidate_category = canonical_category(
        category=category,
        sub_category=sub_category,
        product_name=product_name,
    )

    total_category_purchases = sum(
        profile.category_counts.values()
    )

    if candidate_category and total_category_purchases:
        category_count = profile.category_counts.get(
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

        score = 0.05 + 0.10 * category_affinity

        return round(
            max(0.0, min(score, 1.0)),
            4,
        )

    return 0.1


def usual_quantity_from_profile(
    product_id: int,
    profile: PersonalizationProfile,
) -> int:
    average_quantity = profile.product_average_quantity.get(
        product_id,
        1.0,
    )

    return max(
        1,
        min(
            3,
            int(average_quantity + 0.5),
        ),
    )

def build_basket_candidates(
    products: list[Product],
    purchases: list[Purchase],
) -> list[dict]:
    if not purchases:
        utility_by_product = {
            product.id: 0.5
            for product in products
        }
    else:
        profile = build_personalization_profile(
            purchases
        )

        reference_date = _reference_date(
            purchases,
            None,
        )

        utility_by_product = {
            product.id: personalized_utility_from_profile(
                product,
                profile,
                reference_date,
            )
            for product in products
        }

    return [
        {
            "product": product,
            "utility": utility_by_product[product.id],
        }
        for product in products
    ]
