from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from app.db.models import Product, Purchase
from app.services.decision_features import PriceFeatures
from app.services.decision_prior import (
    ProductPrior,
    build_product_prior,
)
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
class M1DecisionDataset:
    """Supervised dataset containing point-in-time product priors."""

    features: list[PriceFeatures]
    priors: list[ProductPrior]
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


@dataclass(frozen=True)
class _M1DatasetExample:
    """Internal M1 example with its point-in-time product prior."""

    features: PriceFeatures
    prior: ProductPrior
    target: str
    product_id: int
    current_date: date
    future_date: date


class DecisionDatasetBuilder:
    """
    Build supervised price-direction datasets from Dunnhumby data.

    Each product contributes examples generated from its historical
    weekly price observations.

    The final datasets are sorted chronologically by current_date so
    downstream chronological train/test splits operate on actual time
    order rather than product iteration order.
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

    def _group_purchases(
        self,
        purchases: list[Purchase],
    ) -> dict[int, list[Purchase]]:
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

        return purchases_by_product

    def build(
        self,
        products: list[Product],
        purchases: list[Purchase],
    ) -> DecisionDataset:
        """
        Build the M0 dataset from all eligible products.

        Products without enough weekly price observations are skipped.
        """

        purchases_by_product = self._group_purchases(
            purchases
        )

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

    def build_m1(
        self,
        products: list[Product],
        purchases: list[Purchase],
    ) -> M1DecisionDataset:
        """
        Build an M1 dataset with point-in-time product priors.

        Each prior uses only price-direction observations that occur
        before the current prediction date.
        """

        purchases_by_product = self._group_purchases(
            purchases
        )

        examples: list[_M1DatasetExample] = []

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

            ordered_points = sorted(
                weekly_history.points,
                key=lambda point: point.date,
            )

            training_examples = (
                self.training_builder.build_examples(
                    ordered_points
                )
            )

            for example in training_examples:
                historical_targets: list[str] = []

                for index in range(
                    self.training_builder.lookback_weeks,
                    len(ordered_points),
                ):
                    current = ordered_points[index]

                    if current.date >= example.current_date:
                        break

                    future_index = (
                        index
                        + self.training_builder.forecast_horizon_weeks
                    )

                    if future_index >= len(ordered_points):
                        break

                    future = ordered_points[future_index]

                    historical_targets.append(
                        self.training_builder._target(
                            current_price=current.unit_price,
                            future_price=future.unit_price,
                        )
                    )

                prior = build_product_prior(
                    historical_targets
                )

                examples.append(
                    _M1DatasetExample(
                        features=example.features,
                        prior=prior,
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

        return M1DecisionDataset(
            features=[
                example.features
                for example in examples
            ],
            priors=[
                example.prior
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