from __future__ import annotations

from dataclasses import dataclass

from app.ml.forecasting import PricePoint
from app.services.decision_features import (
    PriceFeatures,
    build_price_features,
)


@dataclass(frozen=True)
class TrainingExample:
    """A supervised training example for price direction."""

    features: PriceFeatures
    target: str
    current_date: object
    future_date: object


class PriceTrainingBuilder:
    """
    Build supervised learning examples from historical price data.

    Each example uses a historical lookback window to predict the
    price direction several weeks into the future.
    """

    INCREASE = "INCREASE"
    STABLE = "STABLE"
    DECREASE = "DECREASE"

    def __init__(
        self,
        lookback_weeks: int = 4,
        forecast_horizon_weeks: int = 4,
        stable_threshold: float = 0.02,
    ):
        if lookback_weeks < 1:
            raise ValueError(
                "lookback_weeks must be at least 1"
            )

        if forecast_horizon_weeks < 1:
            raise ValueError(
                "forecast_horizon_weeks must be at least 1"
            )

        if stable_threshold < 0:
            raise ValueError(
                "stable_threshold must be non-negative"
            )

        self.lookback_weeks = lookback_weeks
        self.forecast_horizon_weeks = (
            forecast_horizon_weeks
        )
        self.stable_threshold = stable_threshold

    def _target(
        self,
        current_price: float,
        future_price: float,
    ) -> str:
        """Convert future price movement into a direction label."""

        if current_price <= 0:
            return self.STABLE

        change = (
            future_price - current_price
        ) / current_price

        if change > self.stable_threshold:
            return self.INCREASE

        if change < -self.stable_threshold:
            return self.DECREASE

        return self.STABLE

    def build_examples(
        self,
        history: list[PricePoint],
    ) -> list[TrainingExample]:
        """
        Build chronological training examples from price history.

        A training example requires:

        - lookback_weeks + 1 historical observations
        - one future observation at forecast_horizon_weeks
          after the current observation
        """

        if not history:
            return []

        ordered = sorted(
            history,
            key=lambda point: point.date,
        )

        examples: list[TrainingExample] = []

        minimum_history = (
            self.lookback_weeks
            + self.forecast_horizon_weeks
            + 1
        )

        if len(ordered) < minimum_history:
            return []

        for current_index in range(
            self.lookback_weeks,
            len(ordered)
            - self.forecast_horizon_weeks,
        ):
            window_start = (
                current_index
                - self.lookback_weeks
            )

            window = ordered[
                window_start : current_index + 1
            ]

            current = ordered[current_index]

            future_index = (
                current_index
                + self.forecast_horizon_weeks
            )

            future = ordered[future_index]

            features = build_price_features(
                history=window,
            )

            if features is None:
                continue

            target = self._target(
                current_price=current.unit_price,
                future_price=future.unit_price,
            )

            examples.append(
                TrainingExample(
                    features=features,
                    target=target,
                    current_date=current.date,
                    future_date=future.date,
                )
            )

        return examples


def build_training_data(
    history: list[PricePoint],
    lookback_weeks: int = 4,
    forecast_horizon_weeks: int = 4,
    stable_threshold: float = 0.02,
) -> tuple[
    list[PriceFeatures],
    list[str],
]:
    """
    Build model-ready features and targets from price history.
    """

    builder = PriceTrainingBuilder(
        lookback_weeks=lookback_weeks,
        forecast_horizon_weeks=forecast_horizon_weeks,
        stable_threshold=stable_threshold,
    )

    examples = builder.build_examples(history)

    features = [
        example.features
        for example in examples
    ]

    targets = [
        example.target
        for example in examples
    ]

    return features, targets