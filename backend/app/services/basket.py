"""One place that decides which products a user's basket can contain, and optimises it.

Both the basket page (/api/basket/optimize) and the chat assistant use these functions,
so the two features can never disagree about what "your basket" means.
"""
from __future__ import annotations

import time

from sqlalchemy.orm import Session

from app.db.repositories.products import list_basket_products
from app.db.repositories.purchases import get_user_purchases
from app.ml.optimizer import BasketItem, optimize_basket
from app.services.personalization import (
    build_personalization_profile,
    personalized_utility_from_fields,
    usual_quantity_from_profile,
)

MAX_DISTINCT_PRODUCTS = 14


def build_basket_candidates(
    db: Session, user_id: int, timings: dict | None = None
) -> tuple[list[BasketItem], int]:
    """Return the products this user's basket may include, scored by their purchase habits,
    plus how many purchases the scores are based on.

    If `timings` is given, the milliseconds spent loading and scoring are recorded in it.
    """
    started = time.perf_counter()
    products = list_basket_products(db)
    purchases = get_user_purchases(db, user_id)
    loaded = time.perf_counter()
    profile = build_personalization_profile(purchases)
    reference_date = max(
        (p.purchased_at for p in purchases if p.purchased_at is not None),
        default=None,
    )

    candidates = []
    for product in products:
        utility = 0.5
        if reference_date is not None:
            utility = personalized_utility_from_fields(
                product_id=product.id,
                category=product.category,
                sub_category=product.sub_category,
                product_name=product.name,
                profile=profile,
                reference_date=reference_date,
            )
        usual_quantity = usual_quantity_from_profile(product.id, profile)
        candidates.append(
            BasketItem(
                product_id=product.id,
                name=product.name,
                unit_price=float(product.unit_price),
                utility=utility,
                usual_quantity=usual_quantity,
                max_quantity=usual_quantity,
            )
        )
    if timings is not None:
        timings["load"] = (loaded - started) * 1000
        timings["score"] = (time.perf_counter() - loaded) * 1000
    return candidates, len(purchases)


def optimize_for_user(db: Session, user_id: int, budget: float, timings: dict | None = None) -> dict:
    candidates, purchase_count = build_basket_candidates(db, user_id, timings)
    solve_started = time.perf_counter()
    result = optimize_basket(candidates, budget, max_distinct_products=MAX_DISTINCT_PRODUCTS)
    if timings is not None:
        timings["solve"] = (time.perf_counter() - solve_started) * 1000
    return {
        "user_id": user_id,
        "items": [
            {
                "product_id": item.product_id,
                "name": item.name,
                "qty": quantity,
                "unit_price": item.unit_price,
                "utility": item.utility,
            }
            for item, quantity in result.items
        ],
        "total_cost": result.total_cost,
        "total_utility": result.total_utility,
        "candidate_count": len(candidates),
        "purchase_history_count": purchase_count,
    }
