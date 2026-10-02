from collections import Counter

from app.db.models import Product, Purchase
from app.db.session import SessionLocal
from app.services.decision_dataset import (
    DecisionDatasetBuilder,
)
from app.services.decision_evaluation import (
    chronological_split,
)
from app.services.decision_model import (
    DECREASE,
    INCREASE,
    STABLE,
)


DUNNHUMBY_SOURCE = "dunnhumby_complete_journey"

TEST_RATIO = 0.20
GAP = 4


def print_distribution(
    name: str,
    targets: list[str],
) -> None:
    counts = Counter(targets)

    print()
    print(name)

    for target in (
        INCREASE,
        STABLE,
        DECREASE,
    ):
        count = counts[target]

        percentage = (
            count / len(targets) * 100
            if targets
            else 0.0
        )

        print(
            f"  {target:8s}: "
            f"{count:6d} "
            f"({percentage:5.1f}%)"
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

        print()
        print("=" * 60)
        print("REAL DECISION DATASET")
        print("=" * 60)

        print(
            f"Training examples: "
            f"{dataset.sample_count}"
        )

        unique_products = set(
            dataset.product_ids
        )

        print(
            f"Products contributing data: "
            f"{len(unique_products)}"
        )

        if dataset.current_dates:
            print(
                f"First current date: "
                f"{min(dataset.current_dates)}"
            )
            print(
                f"Last current date:  "
                f"{max(dataset.current_dates)}"
            )

        print_distribution(
            "Overall target distribution:",
            dataset.targets,
        )

        (
            train_features,
            test_features,
            train_targets,
            test_targets,
        ) = chronological_split(
            features=dataset.features,
            targets=dataset.targets,
            test_ratio=TEST_RATIO,
            gap=GAP,
        )

        print()
        print("=" * 60)
        print("CHRONOLOGICAL EVALUATION SPLIT")
        print("=" * 60)

        print(
            f"Train examples: "
            f"{len(train_features)}"
        )
        print(
            f"Gap examples:   "
            f"{GAP}"
        )
        print(
            f"Test examples:  "
            f"{len(test_features)}"
        )

        print_distribution(
            "Training target distribution:",
            train_targets,
        )

        print_distribution(
            "Test target distribution:",
            test_targets,
        )

        train_products = set(
            dataset.product_ids[:len(train_features)]
        )

        test_start = (
            len(dataset.features)
            - len(test_features)
        )

        test_products = set(
            dataset.product_ids[test_start:]
        )

        print()
        print(
            f"Products in training period: "
            f"{len(train_products)}"
        )
        print(
            f"Products in test period:     "
            f"{len(test_products)}"
        )

    finally:
        db.close()


if __name__ == "__main__":
    main()
