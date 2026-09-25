from __future__ import annotations

from app.db.models import Product, Purchase
from app.ml.forecasting import price_trend
from app.services.decision_engine import (
    DecisionEvidence,
    DecisionResult,
    make_decision,
)
from app.services.price_intelligence import (
    build_product_price_history,
)
from app.services.similarity import (
    find_cheaper_substitutes,
)


def make_product_decision(
    product: Product,
    purchases: list[Purchase],
    products: list[Product],
    forecast_horizon_weeks: int = 4,
    top_k_substitutes: int = 5,
) -> DecisionResult:
    """
    Generate a purchasing decision for a product.

    This service orchestrates existing intelligence components:

        price history
            ↓
        price forecast
            ↓
        cheaper substitutes
            ↓
        deterministic decision engine

    The decision engine itself remains independent of the database
    and ML/service implementations.
    """

    history = build_product_price_history(
        product=product,
        purchases=purchases,
    )

    forecast = price_trend(
        history=history.points,
        forecast_horizon_weeks=forecast_horizon_weeks,
    )

    substitutes = find_cheaper_substitutes(
        product=product,
        products=products,
        purchases=purchases,
        top_k=top_k_substitutes,
    )

    best_substitute = (
        substitutes[0]
        if substitutes
        else None
    )

    evidence = DecisionEvidence(
        current_price=(
            forecast["current_price"]
            if forecast["current_price"] is not None
            else product.unit_price
        ),
        forecast_price=forecast["forecast_price"],
        forecast_change_percent=forecast[
            "forecast_change_percent"
        ],
        forecast_confidence=forecast["confidence"],
        substitute_similarity=(
            best_substitute["similarity"]
            if best_substitute is not None
            else None
        ),
        substitute_savings_percent=(
            best_substitute["savings_percent"]
            if best_substitute is not None
            else None
        ),
    )

    return make_decision(evidence)
