from pathlib import Path

from app.db.models import Product, Purchase
from app.db.session import SessionLocal
from app.services.decision_dataset import (
    DUNNHUMBY_SOURCE,
    DecisionDatasetBuilder,
)
from app.services.decision_evaluation import (
    chronological_time_split,
)
from app.services.decision_model import (
    PriceDirectionModel,
)
from app.services.decision_model_store import (
    save_m1_model,
)


TEST_RATIO = 0.20
GAP_WEEKS = 4

LOOKBACK_WEEKS = 4
FORECAST_HORIZON_WEEKS = 4
STABLE_THRESHOLD = 0.02
MIN_WEEKLY_OBSERVATIONS = 9

MODEL_PATH = Path(
    "data/models/decision_m1.joblib"
)


def load_dunnhumby_data(
    session,
) -> tuple[list[Product], list[Purchase]]:
    products = (
        session.query(Product)
        .filter(
            Product.source
            == DUNNHUMBY_SOURCE
        )
        .all()
    )

    purchases = (
        session.query(Purchase)
        .filter(
            Purchase.source
            == DUNNHUMBY_SOURCE
        )
        .all()
    )

    return products, purchases


def main() -> None:
    print(
        "Loading Dunnhumby training data..."
    )

    with SessionLocal() as session:
        products, purchases = (
            load_dunnhumby_data(session)
        )

    print(
        f"Products: {len(products)}"
    )
    print(
        f"Purchases: {len(purchases)}"
    )

    builder = DecisionDatasetBuilder(
        lookback_weeks=LOOKBACK_WEEKS,
        forecast_horizon_weeks=(
            FORECAST_HORIZON_WEEKS
        ),
        stable_threshold=STABLE_THRESHOLD,
        min_weekly_observations=(
            MIN_WEEKLY_OBSERVATIONS
        ),
    )

    dataset = builder.build_m1(
        products=products,
        purchases=purchases,
    )

    if dataset.sample_count < 10:
        raise RuntimeError(
            "M1 dataset contains fewer than "
            "10 examples"
        )

    print(
        f"M1 dataset examples: "
        f"{dataset.sample_count}"
    )

    (
        training_features,
        test_features,
        training_targets,
        test_targets,
    ) = chronological_time_split(
        features=dataset.features,
        targets=dataset.targets,
        current_dates=dataset.current_dates,
        test_ratio=TEST_RATIO,
        gap_weeks=GAP_WEEKS,
    )

    if not training_features:
        raise RuntimeError(
            "M1 training split is empty"
        )

    if not test_features:
        raise RuntimeError(
            "M1 test split is empty"
        )

    training_count = len(
        training_features
    )

    test_count = len(
        test_features
    )

    print(
        f"Training examples: "
        f"{training_count}"
    )
    print(
        f"Test examples: "
        f"{test_count}"
    )

    training_end_index = (
        training_count - 1
    )

    print(
        "Training period: "
        f"{dataset.current_dates[0]} "
        f"-> "
        f"{dataset.current_dates[training_end_index]}"
    )

    test_start_index = (
        dataset.sample_count
        - test_count
    )

    print(
        "Test period: "
        f"{dataset.current_dates[test_start_index]} "
        f"-> "
        f"{dataset.current_dates[-1]}"
    )

    training_priors = [
        dataset.priors[index]
        for index in range(
            training_count
        )
    ]

    model = PriceDirectionModel(
        stable_threshold=STABLE_THRESHOLD,
    )

    model.fit_m1(
        features=training_features,
        priors=training_priors,
        targets=training_targets,
    )

    save_m1_model(
        model=model,
        path=MODEL_PATH,
    )

    print(
        f"M1 model saved to: {MODEL_PATH}"
    )


if __name__ == "__main__":
    main()
