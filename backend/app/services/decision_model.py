from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from app.services.decision_features import (
    PriceFeatures,
    feature_vector,
)


INCREASE = "INCREASE"
STABLE = "STABLE"
DECREASE = "DECREASE"

STATES = (
    INCREASE,
    STABLE,
    DECREASE,
)


@dataclass(frozen=True)
class PriceProbability:
    """Probabilistic belief over future price states."""

    increase: float
    stable: float
    decrease: float

    def as_dict(self) -> dict[str, float]:
        return {
            INCREASE: self.increase,
            STABLE: self.stable,
            DECREASE: self.decrease,
        }


class PriceDirectionModel:
    """
    Probabilistic price-direction classifier.

    The model predicts whether the future price is expected to:

    - INCREASE
    - STAY STABLE
    - DECREASE

    Logistic regression is used as the first baseline because it is:

    - interpretable
    - probabilistic
    - fast
    - easy to evaluate
    - easy to calibrate later
    """

    def __init__(
        self,
        stable_threshold: float = 0.02,
    ):
        self.stable_threshold = stable_threshold

        self.model = Pipeline(
            [
                (
                    "scaler",
                    StandardScaler(),
                ),
                (
                    "classifier",
                    LogisticRegression(
                        max_iter=1000,
                    ),
                ),
            ]
        )

        self._fitted = False

    def _target(
        self,
        current_price: float,
        future_price: float,
    ) -> str:
        """
        Convert a future price movement into a classification target.

        A movement within +/- stable_threshold is considered STABLE.
        """

        if current_price <= 0:
            return STABLE

        change = (
            future_price - current_price
        ) / current_price

        if change > self.stable_threshold:
            return INCREASE

        if change < -self.stable_threshold:
            return DECREASE

        return STABLE

    def build_training_target(
        self,
        current_price: float,
        future_price: float,
    ) -> str:
        """Build a training label from current and future prices."""

        return self._target(
            current_price,
            future_price,
        )

    def fit(
        self,
        features: list[PriceFeatures],
        targets: list[str],
    ) -> None:
        """
        Fit the probabilistic classifier.

        At least two classes must be present in the training data.
        """

        if len(features) != len(targets):
            raise ValueError(
                "features and targets must have equal length"
            )

        if len(features) < 10:
            raise ValueError(
                "At least 10 training examples are required"
            )

        invalid_targets = set(targets) - set(STATES)

        if invalid_targets:
            raise ValueError(
                f"Unknown training targets: {sorted(invalid_targets)}"
            )

        if len(set(targets)) < 2:
            raise ValueError(
                "Training data must contain at least "
                "two price-direction classes"
            )

        X = np.asarray(
            [
                feature_vector(item)
                for item in features
            ],
            dtype=float,
        )

        self.model.fit(
            X,
            targets,
        )

        self._fitted = True

    def predict_proba(
        self,
        features: PriceFeatures,
    ) -> PriceProbability:
        """
        Return the model's probability distribution over price states.
        """

        if not self._fitted:
            raise RuntimeError(
                "PriceDirectionModel must be fitted before prediction"
            )

        probabilities = self.model.predict_proba(
            np.asarray(
                [feature_vector(features)],
                dtype=float,
            )
        )[0]

        classes = self.model.named_steps[
            "classifier"
        ].classes_

        values = {
            state: 0.0
            for state in STATES
        }

        for state, probability in zip(
            classes,
            probabilities,
        ):
            values[state] = float(probability)

        return PriceProbability(
            increase=round(
                values[INCREASE],
                4,
            ),
            stable=round(
                values[STABLE],
                4,
            ),
            decrease=round(
                values[DECREASE],
                4,
            ),
        )