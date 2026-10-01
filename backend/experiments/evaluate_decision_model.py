from collections import Counter

import numpy as np
from scipy.optimize import minimize_scalar
from sklearn.metrics import log_loss

from app.db.models import Product, Purchase
from app.db.session import SessionLocal
from app.services.decision_dataset import DecisionDatasetBuilder
from app.services.decision_evaluation import (
    chronological_time_split,
    evaluate_model,
    evaluate_probabilities,
)
from app.services.decision_features import feature_vector
from app.services.decision_model import PriceDirectionModel


DUNNHUMBY_SOURCE = "dunnhumby_complete_journey"

TEST_RATIO = 0.20
CALIBRATION_RATIO = 0.20
GAP_WEEKS = 4

LABELS = [
    "INCREASE",
    "STABLE",
    "DECREASE",
]


def majority_baseline_accuracy(
    targets: list[str],
) -> float:
    if not targets:
        return 0.0

    counts = Counter(targets)

    return max(counts.values()) / len(targets)


def chronological_calibration_split(
    features: list,
    targets: list[str],
    current_dates: list,
    calibration_ratio: float,
) -> tuple[list, list, list[str], list[str]]:
    if not 0.0 < calibration_ratio < 1.0:
        raise ValueError(
            "calibration_ratio must be between 0 and 1"
        )

    if not (
        len(features)
        == len(targets)
        == len(current_dates)
    ):
        raise ValueError(
            "features, targets, and current_dates "
            "must have equal length"
        )

    if len(features) < 2:
        raise ValueError(
            "At least two examples are required"
        )

    calibration_count = max(
        1,
        int(
            round(
                len(features) * calibration_ratio
            )
        ),
    )

    split_index = len(features) - calibration_count

    if split_index <= 0:
        raise ValueError(
            "Not enough examples for calibration split"
        )

    return (
        features[:split_index],
        features[split_index:],
        targets[:split_index],
        targets[split_index:],
    )


def build_feature_matrix(
    features: list,
) -> np.ndarray:
    return np.asarray(
        [
            feature_vector(feature)
            for feature in features
        ],
        dtype=float,
    )


def get_model_probabilities(
    model: PriceDirectionModel,
    features: list,
) -> np.ndarray:
    if not features:
        raise ValueError(
            "At least one feature is required"
        )

    X = build_feature_matrix(features)

    return model.model.predict_proba(X)


def temperature_scale(
    probabilities: np.ndarray,
    temperature: float,
) -> np.ndarray:
    if temperature <= 0:
        raise ValueError(
            "temperature must be positive"
        )

    probabilities = np.asarray(
        probabilities,
        dtype=float,
    )

    probabilities = np.clip(
        probabilities,
        1e-12,
        1.0,
    )

    log_probabilities = np.log(
        probabilities
    )

    scaled = (
        log_probabilities / temperature
    )

    scaled -= np.max(
        scaled,
        axis=1,
        keepdims=True,
    )

    exponentials = np.exp(scaled)

    return (
        exponentials
        / np.sum(
            exponentials,
            axis=1,
            keepdims=True,
        )
    )


def fit_temperature(
    probabilities: np.ndarray,
    targets: list[str],
) -> float:
    if len(probabilities) != len(targets):
        raise ValueError(
            "probabilities and targets "
            "must have equal length"
        )

    if not targets:
        raise ValueError(
            "At least one calibration example is required"
        )

    target_indices = np.asarray(
        [
            LABELS.index(target)
            for target in targets
        ],
        dtype=int,
    )

    def objective(
        temperature: float,
    ) -> float:
        calibrated = temperature_scale(
            probabilities=probabilities,
            temperature=temperature,
        )

        return float(
            log_loss(
                target_indices,
                calibrated,
                labels=np.arange(len(LABELS)),
            )
        )

    result = minimize_scalar(
        objective,
        bounds=(0.05, 10.0),
        method="bounded",
    )

    if not result.success:
        raise RuntimeError(
            "Temperature calibration failed"
        )

    return float(result.x)


def calculate_probability_metrics(
    probabilities: np.ndarray,
    targets: list[str],
) -> tuple[float, float]:
    if len(probabilities) != len(targets):
        raise ValueError(
            "probabilities and targets "
            "must have equal length"
        )

    target_indices = np.asarray(
        [
            LABELS.index(target)
            for target in targets
        ],
        dtype=int,
    )

    probability_log_loss = float(
        log_loss(
            target_indices,
            probabilities,
            labels=np.arange(len(LABELS)),
        )
    )

    one_hot = np.zeros_like(
        probabilities
    )

    one_hot[
        np.arange(len(targets)),
        target_indices,
    ] = 1.0

    brier_score = float(
        np.mean(
            np.sum(
                (
                    probabilities - one_hot
                ) ** 2,
                axis=1,
            )
        )
    )

    return (
        probability_log_loss,
        brier_score,
    )


def main() -> None:
    db = SessionLocal()

    try:
        print("=" * 60)
        print("LOADING DUNNHUMBY DATA")
        print("=" * 60)

        products = (
            db.query(Product)
            .filter(
                Product.source == DUNNHUMBY_SOURCE
            )
            .all()
        )

        purchases = (
            db.query(Purchase)
            .filter(
                Purchase.source == DUNNHUMBY_SOURCE
            )
            .order_by(Purchase.purchased_at)
            .all()
        )

        print(f"Products:  {len(products)}")
        print(f"Purchases: {len(purchases)}")

        builder = DecisionDatasetBuilder(
            lookback_weeks=4,
            forecast_horizon_weeks=4,
            stable_threshold=0.02,
            min_weekly_observations=9,
        )

        dataset = builder.build(
            products=products,
            purchases=purchases,
        )

        (
            pre_test_features,
            test_features,
            pre_test_targets,
            test_targets,
        ) = chronological_time_split(
            features=dataset.features,
            targets=dataset.targets,
            current_dates=dataset.current_dates,
            test_ratio=TEST_RATIO,
            gap_weeks=GAP_WEEKS,
        )

        pre_test_count = len(
            pre_test_features
        )

        pre_test_dates = (
            dataset.current_dates[:pre_test_count]
        )

        test_start_index = (
            dataset.sample_count
            - len(test_features)
        )

        test_dates = (
            dataset.current_dates[test_start_index:]
        )

        (
            train_features,
            calibration_features,
            train_targets,
            calibration_targets,
        ) = chronological_calibration_split(
            features=pre_test_features,
            targets=pre_test_targets,
            current_dates=pre_test_dates,
            calibration_ratio=CALIBRATION_RATIO,
        )

        train_dates = pre_test_dates[
            :len(train_features)
        ]

        calibration_dates = pre_test_dates[
            len(train_features):
        ]

        print()
        print("=" * 60)
        print("DATASET")
        print("=" * 60)

        print(
            f"Total examples: "
            f"{dataset.sample_count}"
        )

        print(
            f"Train examples: "
            f"{len(train_features)}"
        )

        print(
            f"Calibration examples: "
            f"{len(calibration_features)}"
        )

        print(
            f"Test examples:  "
            f"{len(test_features)}"
        )

        print(
            f"Training period: "
            f"{min(train_dates)}"
            f" → "
            f"{max(train_dates)}"
        )

        print(
            f"Calibration period: "
            f"{min(calibration_dates)}"
            f" → "
            f"{max(calibration_dates)}"
        )

        print(
            f"Temporal embargo: "
            f"{GAP_WEEKS} weeks"
        )

        print(
            f"Test period:     "
            f"{min(test_dates)}"
            f" → "
            f"{max(test_dates)}"
        )

        baseline_accuracy = (
            majority_baseline_accuracy(
                test_targets
            )
        )

        print()
        print("=" * 60)
        print("BASELINE")
        print("=" * 60)

        print(
            "Strategy: always predict majority class"
        )

        print(
            f"Baseline accuracy: "
            f"{baseline_accuracy:.4f}"
        )

        print()
        print("=" * 60)
        print("TRAINING LOGISTIC REGRESSION")
        print("=" * 60)

        model = PriceDirectionModel()

        model.fit(
            features=train_features,
            targets=train_targets,
        )

        result = evaluate_model(
            model=model,
            features=test_features,
            targets=test_targets,
        )

        probability_result = (
            evaluate_probabilities(
                model=model,
                features=test_features,
                targets=test_targets,
            )
        )

        print()
        print("=" * 60)
        print("MODEL RESULTS")
        print("=" * 60)

        print(
            f"Accuracy: "
            f"{result.accuracy:.4f}"
        )

        print(
            f"Accuracy improvement over baseline: "
            f"{result.accuracy - baseline_accuracy:+.4f}"
        )

        print(
            f"Test examples: "
            f"{result.sample_count}"
        )

        print()
        print("Confusion matrix")

        print(
            "Rows = actual, columns = predicted"
        )

        print(
            "Labels: [INCREASE, STABLE, DECREASE]"
        )

        for row in result.confusion_matrix:
            print(f"  {row}")

        print()
        print("Classification report")

        report = result.classification_report

        for label in LABELS:
            metrics = report[label]

            print(
                f"  {label:8s} "
                f"precision={metrics['precision']:.4f} "
                f"recall={metrics['recall']:.4f} "
                f"f1={metrics['f1-score']:.4f}"
            )

        print()

        print(
            f"  macro avg "
            f"precision={report['macro avg']['precision']:.4f} "
            f"recall={report['macro avg']['recall']:.4f} "
            f"f1={report['macro avg']['f1-score']:.4f}"
        )

        print()
        print("=" * 60)
        print("RAW PROBABILITY QUALITY")
        print("=" * 60)

        print(
            f"Log loss: "
            f"{probability_result.log_loss:.4f}"
        )

        print(
            f"Multiclass Brier score: "
            f"{probability_result.brier_score:.4f}"
        )

        calibration_probabilities = (
            get_model_probabilities(
                model=model,
                features=calibration_features,
            )
        )

        test_probabilities = (
            get_model_probabilities(
                model=model,
                features=test_features,
            )
        )

        temperature = fit_temperature(
            probabilities=calibration_probabilities,
            targets=calibration_targets,
        )

        calibrated_test_probabilities = (
            temperature_scale(
                probabilities=test_probabilities,
                temperature=temperature,
            )
        )

        raw_log_loss, raw_brier_score = (
            calculate_probability_metrics(
                probabilities=test_probabilities,
                targets=test_targets,
            )
        )

        calibrated_log_loss, calibrated_brier_score = (
            calculate_probability_metrics(
                probabilities=calibrated_test_probabilities,
                targets=test_targets,
            )
        )

        print()
        print("=" * 60)
        print("TEMPERATURE CALIBRATION")
        print("=" * 60)

        print(
            f"Calibration examples: "
            f"{len(calibration_features)}"
        )

        print(
            f"Learned temperature: "
            f"{temperature:.4f}"
        )

        if temperature > 1.0:
            print(
                "Effect: probabilities are softened"
            )
        elif temperature < 1.0:
            print(
                "Effect: probabilities are sharpened"
            )
        else:
            print(
                "Effect: probabilities are unchanged"
            )

        print()
        print("=" * 60)
        print("CALIBRATED TEST PROBABILITY QUALITY")
        print("=" * 60)

        print(
            f"Raw log loss: "
            f"{raw_log_loss:.4f}"
        )

        print(
            f"Calibrated log loss: "
            f"{calibrated_log_loss:.4f}"
        )

        print(
            f"Log loss improvement: "
            f"{raw_log_loss - calibrated_log_loss:+.4f}"
        )

        print()

        print(
            f"Raw Brier score: "
            f"{raw_brier_score:.4f}"
        )

        print(
            f"Calibrated Brier score: "
            f"{calibrated_brier_score:.4f}"
        )

        print(
            f"Brier improvement: "
            f"{raw_brier_score - calibrated_brier_score:+.4f}"
        )

    finally:
        db.close()


if __name__ == "__main__":
    main()