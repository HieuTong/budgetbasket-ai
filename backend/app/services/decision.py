from __future__ import annotations

from app.db.models import Product, Purchase
from app.ml.forecasting import price_trend
from app.services.decision_engine import (
    DecisionEvidence,
    DecisionResult,
    make_decision,
)
from app.services.decision_features import build_price_features
from app.services.decision_model_runtime import get_m1_model
from app.services.decision_prior import build_product_prior
from app.services.price_intelligence import (
    aggregate_weekly_price_history,
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

    weekly_history = aggregate_weekly_price_history(
        history
    )

    price_features = build_price_features(
        history=weekly_history.points,
        forecast_change_percent=forecast[
            "forecast_change_percent"
        ],
        forecast_confidence=forecast[
            "confidence"
        ],
    )

    price_probability = None

    if price_features is not None:
        current_date = weekly_history.points[-1].date

        historical_targets = []

        for index in range(
            4,
            len(weekly_history.points),
        ):
            current = weekly_history.points[index]

            if current.date >= current_date:
                break

            future_index = index + 4

            if future_index >= len(weekly_history.points):
                break

            future = weekly_history.points[future_index]

            change = (
                (future.unit_price - current.unit_price)
                / current.unit_price
                if current.unit_price > 0
                else 0.0
            )

            if change > 0.02:
                historical_targets.append(
                    "INCREASE"
                )
            elif change < -0.02:
                historical_targets.append(
                    "DECREASE"
                )
            else:
                historical_targets.append(
                    "STABLE"
                )

        prior = build_product_prior(
            historical_targets
        )

        try:
            model = get_m1_model()
            price_probability = model.predict_proba_m1(
                features=price_features,
                prior=prior,
            )
        except FileNotFoundError:
            price_probability = None

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
        price_probability=price_probability,
    )

    return make_decision(evidence)
