from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from app.services.decision_features import (
    PriceFeatures,
    feature_vector,
    m1_feature_vector,
)

if TYPE_CHECKING:
    from app.services.decision_prior import ProductPrior


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

        self.model = self._build_pipeline()
        self.m1_model = self._build_pipeline()

        self._fitted = False
        self._m1_fitted = False

    @staticmethod
    def _build_pipeline() -> Pipeline:
        return Pipeline(
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

    def fit_m1(
        self,
        features: list[PriceFeatures],
        priors: list[ProductPrior],
        targets: list[str],
    ) -> None:
        """
        Fit the M1 classifier using price features and product priors.

        M1 extends the nine M0 features with four prior features.
        """

        if len(features) != len(priors):
            raise ValueError(
                "features and priors must have equal length"
            )

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
                m1_feature_vector(
                    item,
                    prior,
                )
                for item, prior in zip(
                    features,
                    priors,
                )
            ],
            dtype=float,
        )

        self.m1_model.fit(
            X,
            targets,
        )

        self._m1_fitted = True

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

        return self._probability_from_model(
            self.model,
            probabilities,
        )

    def predict_proba_m1(
        self,
        features: PriceFeatures,
        prior: ProductPrior,
    ) -> PriceProbability:
        """
        Return the M1 probability distribution over price states.
        """

        if not self._m1_fitted:
            raise RuntimeError(
                "M1 PriceDirectionModel must be fitted before prediction"
            )

        probabilities = self.m1_model.predict_proba(
            np.asarray(
                [
                    m1_feature_vector(
                        features,
                        prior,
                    )
                ],
                dtype=float,
            )
        )[0]

        return self._probability_from_model(
            self.m1_model,
            probabilities,
        )

    @staticmethod
    def _probability_from_model(
        model: Pipeline,
        probabilities: np.ndarray,
    ) -> PriceProbability:
        classes = model.named_steps[
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