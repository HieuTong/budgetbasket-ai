from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from app.db.models import Product, Purchase
from app.services.decision_features import PriceFeatures
from app.services.decision_training import (
    PriceTrainingBuilder,
)
from app.services.price_intelligence import (
    aggregate_weekly_price_history,
    build_product_price_history,
)


DUNNHUMBY_SOURCE = "dunnhumby_complete_journey"


@dataclass(frozen=True)
class DecisionDataset:
    """Combined supervised dataset for price-direction prediction."""

    features: list[PriceFeatures]
    targets: list[str]
    product_ids: list[int]
    current_dates: list[date]
    future_dates: list[date]

    @property
    def sample_count(self) -> int:
        return len(self.features)


@dataclass(frozen=True)
class _DatasetExample:
    """Internal example used to keep dataset fields aligned."""

    features: PriceFeatures
    target: str
    product_id: int
    current_date: date
    future_date: date


class DecisionDatasetBuilder:
    """
    Build a supervised price-direction dataset from Dunnhumby data.

    Each product contributes training examples generated from its
    historical weekly price observations.

    The final dataset is sorted chronologically by current_date so
    that downstream chronological train/test splits operate on
    actual time order rather than product iteration order.
    """

    def __init__(
        self,
        lookback_weeks: int = 4,
        forecast_horizon_weeks: int = 4,
        stable_threshold: float = 0.02,
        min_weekly_observations: int = 9,
    ):
        if min_weekly_observations < 1:
            raise ValueError(
                "min_weekly_observations must be at least 1"
            )

        self.training_builder = PriceTrainingBuilder(
            lookback_weeks=lookback_weeks,
            forecast_horizon_weeks=forecast_horizon_weeks,
            stable_threshold=stable_threshold,
        )

        self.min_weekly_observations = (
            min_weekly_observations
        )

    def build(
        self,
        products: list[Product],
        purchases: list[Purchase],
    ) -> DecisionDataset:
        """
        Build the combined dataset from all eligible products.

        Products without enough weekly price observations are skipped.

        Examples are sorted by current_date before the dataset is
        returned so chronological evaluation is genuinely time-based.
        """

        purchases_by_product: dict[
            int,
            list[Purchase],
        ] = {}

        for purchase in purchases:
            if (
                purchase.source != DUNNHUMBY_SOURCE
                or purchase.product_id is None
            ):
                continue

            purchases_by_product.setdefault(
                purchase.product_id,
                [],
            ).append(purchase)

        examples: list[_DatasetExample] = []

        for product in products:
            product_purchases = purchases_by_product.get(
                product.id,
                [],
            )

            if not product_purchases:
                continue

            daily_history = build_product_price_history(
                product=product,
                purchases=product_purchases,
            )

            weekly_history = (
                aggregate_weekly_price_history(
                    daily_history
                )
            )

            if (
                len(weekly_history.points)
                < self.min_weekly_observations
            ):
                continue

            training_examples = (
                self.training_builder.build_examples(
                    weekly_history.points
                )
            )

            for example in training_examples:
                examples.append(
                    _DatasetExample(
                        features=example.features,
                        target=example.target,
                        product_id=product.id,
                        current_date=example.current_date,
                        future_date=example.future_date,
                    )
                )

        examples.sort(
            key=lambda example: (
                example.current_date,
                example.product_id,
            )
        )

        return DecisionDataset(
            features=[
                example.features
                for example in examples
            ],
            targets=[
                example.target
                for example in examples
            ],
            product_ids=[
                example.product_id
                for example in examples
            ],
            current_dates=[
                example.current_date
                for example in examples
            ],
            future_dates=[
                example.future_date
                for example in examples
            ],
        )
