from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timedelta

from app.db.models import Purchase


@dataclass
class UserPurchaseProfile:
    user_id: int
    analysis_period_days: int
    transaction_count: int
    unique_products: int
    unique_categories: int
    average_quantity: float
    purchases_per_month: float
    recent_purchase_count: int
    category_frequency: dict[str, int]
    product_frequency: dict[int, int]


def build_purchase_profile(
    user_id: int,
    purchases: list[Purchase],
    now: datetime | None = None,
    analysis_period_days: int = 365,
) -> UserPurchaseProfile:
    now = now or datetime.utcnow()

    user_purchases = [
        purchase
        for purchase in purchases
        if (
            purchase.user_id == user_id
            and purchase.purchased_at is not None
            and purchase.purchased_at
            >= now - timedelta(days=analysis_period_days)
        )
    ]

    if not user_purchases:
        return UserPurchaseProfile(
            user_id=user_id,
            analysis_period_days=analysis_period_days,
            transaction_count=0,
            unique_products=0,
            unique_categories=0,
            average_quantity=0.0,
            purchases_per_month=0.0,
            recent_purchase_count=0,
            category_frequency={},
            product_frequency={},
        )

    product_frequency = Counter(
        purchase.product_id
        for purchase in user_purchases
    )

    category_frequency = Counter(
        purchase.product.category
        for purchase in user_purchases
        if (
            purchase.product is not None
            and purchase.product.category
        )
    )

    total_quantity = sum(
        purchase.quantity or 0.0
        for purchase in user_purchases
    )

    recent_cutoff = now - timedelta(days=30)

    recent_purchase_count = sum(
        1
        for purchase in user_purchases
        if purchase.purchased_at >= recent_cutoff
    )

    months = analysis_period_days / 30.0

    return UserPurchaseProfile(
        user_id=user_id,
        analysis_period_days=analysis_period_days,
        transaction_count=len(user_purchases),
        unique_products=len(product_frequency),
        unique_categories=len(category_frequency),
        average_quantity=round(
            total_quantity / len(user_purchases),
            2,
        ),
        purchases_per_month=round(
            len(user_purchases) / months,
            2,
        ),
        recent_purchase_count=recent_purchase_count,
        category_frequency=dict(category_frequency),
        product_frequency=dict(product_frequency),
    )