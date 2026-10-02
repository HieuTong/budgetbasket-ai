from __future__ import annotations

from collections import Counter
from dataclasses import dataclass

from app.services.decision_model import (
    DECREASE,
    INCREASE,
    STABLE,
)


@dataclass(frozen=True)
class ProductPrior:
    increase: float
    stable: float
    decrease: float
    history_count: int


def build_product_prior(
    history: list[str],
    alpha: float = 1.0,
) -> ProductPrior:
    if alpha <= 0:
        raise ValueError("alpha must be greater than 0")

    counts = Counter(history)
    history_count = len(history)
    denominator = history_count + alpha * 3

    return ProductPrior(
        increase=(
            counts[INCREASE] + alpha
        ) / denominator,
        stable=(
            counts[STABLE] + alpha
        ) / denominator,
        decrease=(
            counts[DECREASE] + alpha
        ) / denominator,
        history_count=history_count,
    )
