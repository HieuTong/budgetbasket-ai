from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta

import numpy as np
from sklearn.metrics import (
    accuracy_score,
    brier_score_loss,
    classification_report,
    confusion_matrix,
    log_loss,
)
from sklearn.preprocessing import label_binarize

from app.services.decision_features import (
    PriceFeatures,
    feature_vector,
)
from app.services.decision_model import (
    DECREASE,
    INCREASE,
    STABLE,
    PriceDirectionModel,
)


LABELS = [
    INCREASE,
    STABLE,
    DECREASE,
]


@dataclass(frozen=True)
class EvaluationResult:
    """Evaluation metrics for the price-direction model."""

    accuracy: float
    sample_count: int
    confusion_matrix: list[list[int]]
    classification_report: dict

    def as_dict(self) -> dict:
        return {
            "accuracy": self.accuracy,
            "sample_count": self.sample_count,
            "confusion_matrix": self.confusion_matrix,
            "classification_report": self.classification_report,
        }


@dataclass(frozen=True)
class ProbabilityEvaluationResult:
    """Evaluation metrics for predicted class probabilities."""

    log_loss: float
    brier_score: float
    sample_count: int

    def as_dict(self) -> dict:
        return {
            "log_loss": self.log_loss,
            "brier_score": self.brier_score,
            "sample_count": self.sample_count,
        }


def chronological_split(
    features: list[PriceFeatures],
    targets: list[str],
    test_ratio: float = 0.20,
    gap: int = 0,
) -> tuple[
    list[PriceFeatures],
    list[PriceFeatures],
    list[str],
    list[str],
]:
    """
    Split time-ordered examples into past training data and
    future test data.

    ``gap`` is retained for backwards compatibility and represents
    a number of examples to remove immediately before the test set.

    For production evaluation of the price-direction model, prefer
    ``chronological_time_split`` so the embargo is expressed in
    calendar time.
    """

    if len(features) != len(targets):
        raise ValueError(
            "features and targets must have equal length"
        )

    if not 0.0 < test_ratio < 1.0:
        raise ValueError(
            "test_ratio must be between 0 and 1"
        )

    if gap < 0:
        raise ValueError(
            "gap must be non-negative"
        )

    if len(features) < 2:
        raise ValueError(
            "At least two examples are required"
        )

    split_index = int(
        len(features) * (1.0 - test_ratio)
    )

    split_index = max(
        1,
        min(
            split_index,
            len(features) - 1,
        ),
    )

    test_start = split_index + gap

    if test_start >= len(features):
        raise ValueError(
            "gap is too large for the available examples"
        )

    return (
        features[:split_index],
        features[test_start:],
        targets[:split_index],
        targets[test_start:],
    )


def chronological_time_split(
    features: list[PriceFeatures],
    targets: list[str],
    current_dates: list[date],
    test_ratio: float = 0.20,
    gap_weeks: int = 0,
) -> tuple[
    list[PriceFeatures],
    list[PriceFeatures],
    list[str],
    list[str],
]:
    """
    Split examples chronologically using actual calendar dates.

    The test period begins after the training period plus a temporal
    embargo of ``gap_weeks``.

    Examples must already be sorted by current date.
    """

    if not (
        len(features)
        == len(targets)
        == len(current_dates)
    ):
        raise ValueError(
            "features, targets, and current_dates "
            "must have equal length"
        )

    if not 0.0 < test_ratio < 1.0:
        raise ValueError(
            "test_ratio must be between 0 and 1"
        )

    if gap_weeks < 0:
        raise ValueError(
            "gap_weeks must be non-negative"
        )

    if len(features) < 2:
        raise ValueError(
            "At least two examples are required"
        )

    for previous, current in zip(
        current_dates,
        current_dates[1:],
    ):
        if current < previous:
            raise ValueError(
                "current_dates must be sorted chronologically"
            )

    split_index = int(
        len(features) * (1.0 - test_ratio)
    )

    split_index = max(
        1,
        min(
            split_index,
            len(features) - 1,
        ),
    )

    training_features = features[:split_index]
    training_targets = targets[:split_index]

    training_end_date = current_dates[
        split_index - 1
    ]

    embargo_end_date = (
        training_end_date
        + timedelta(weeks=gap_weeks)
    )

    test_start_index = split_index

    while (
        test_start_index < len(features)
        and current_dates[test_start_index]
        <= embargo_end_date
    ):
        test_start_index += 1

    if test_start_index >= len(features):
        raise ValueError(
            "gap_weeks is too large for the available examples"
        )

    test_features = features[
        test_start_index:
    ]

    test_targets = targets[
        test_start_index:
    ]

    return (
        training_features,
        test_features,
        training_targets,
        test_targets,
    )


def _feature_matrix(
    features: list[PriceFeatures],
) -> np.ndarray:
    """Convert feature objects into a numeric matrix."""

    return np.asarray(
        [
            feature_vector(item)
            for item in features
        ],
        dtype=float,
    )


def evaluate_model(
    model: PriceDirectionModel,
    features: list[PriceFeatures],
    targets: list[str],
) -> EvaluationResult:
    """
    Evaluate a fitted price-direction model.

    Predictions are compared with the known historical targets.
    """

    if len(features) != len(targets):
        raise ValueError(
            "features and targets must have equal length"
        )

    if not features:
        raise ValueError(
            "At least one evaluation example is required"
        )

    X = _feature_matrix(features)

    predictions = model.model.predict(X)

    accuracy = accuracy_score(
        targets,
        predictions,
    )

    matrix = confusion_matrix(
        targets,
        predictions,
        labels=LABELS,
    )

    report = classification_report(
        targets,
        predictions,
        labels=LABELS,
        output_dict=True,
        zero_division=0,
    )

    return EvaluationResult(
        accuracy=round(
            float(accuracy),
            4,
        ),
        sample_count=len(features),
        confusion_matrix=matrix.tolist(),
        classification_report=report,
    )


def evaluate_probabilities(
    model: PriceDirectionModel,
    features: list[PriceFeatures],
    targets: list[str],
) -> ProbabilityEvaluationResult:
    """
    Evaluate the quality of predicted class probabilities.

    Lower log loss and Brier score indicate better probabilistic
    predictions.
    """

    if len(features) != len(targets):
        raise ValueError(
            "features and targets must have equal length"
        )

    if not features:
        raise ValueError(
            "At least one evaluation example is required"
        )

    X = _feature_matrix(features)

    probabilities = model.model.predict_proba(X)

    classes = model.model.named_steps[
        "classifier"
    ].classes_

    class_to_index = {
        class_name: index
        for index, class_name in enumerate(classes)
    }

    ordered_probabilities = np.zeros(
        (
            len(features),
            len(LABELS),
        ),
        dtype=float,
    )

    for target_index, label in enumerate(LABELS):
        if label in class_to_index:
            ordered_probabilities[
                :,
                target_index,
            ] = probabilities[
                :,
                class_to_index[label],
            ]

    encoded_targets = label_binarize(
        targets,
        classes=LABELS,
    )

    probability_log_loss = log_loss(
        targets,
        ordered_probabilities,
        labels=LABELS,
    )

    brier_scores = []

    for class_index in range(len(LABELS)):
        brier_scores.append(
            brier_score_loss(
                encoded_targets[:, class_index],
                ordered_probabilities[:, class_index],
            )
        )

    multiclass_brier = float(
        np.mean(brier_scores)
    )

    return ProbabilityEvaluationResult(
        log_loss=round(
            float(probability_log_loss),
            4,
        ),
        brier_score=round(
            multiclass_brier,
            4,
        ),
        sample_count=len(features),
    )
