from datetime import date, timedelta

import pytest

from app.ml.forecasting import PricePoint
from app.services.decision_features import (
    build_price_features,
)
from app.services.decision_model import (
    DECREASE,
    INCREASE,
    STABLE,
    PriceDirectionModel,
)


def _history(
    prices: list[float],
) -> list[PricePoint]:
    start = date(2026, 1, 1)

    return [
        PricePoint(
            date=start + timedelta(weeks=index),
            unit_price=price,
            transaction_count=1,
        )
        for index, price in enumerate(prices)
    ]


def _features(
    prices: list[float],
):
    features = build_price_features(
        _history(prices)
    )

    assert features is not None

    return features


def _training_data():
    feature_sets = [
        [
            8.00,
            8.10,
            8.20,
            8.30,
            8.40,
        ],
        [
            7.00,
            7.10,
            7.20,
            7.30,
            7.40,
        ],
        [
            6.00,
            6.10,
            6.20,
            6.30,
            6.40,
        ],
        [
            9.00,
            9.10,
            9.20,
            9.30,
            9.40,
        ],
        [
            5.00,
            5.10,
            5.20,
            5.30,
            5.40,
        ],
        [
            8.40,
            8.30,
            8.20,
            8.10,
            8.00,
        ],
        [
            7.40,
            7.30,
            7.20,
            7.10,
            7.00,
        ],
        [
            6.40,
            6.30,
            6.20,
            6.10,
            6.00,
        ],
        [
            9.40,
            9.30,
            9.20,
            9.10,
            9.00,
        ],
        [
            5.40,
            5.30,
            5.20,
            5.10,
            5.00,
        ],
        [
            8.00,
            8.01,
            8.00,
            8.01,
            8.00,
        ],
        [
            7.00,
            7.01,
            7.00,
            7.01,
            7.00,
        ],
        [
            6.00,
            6.01,
            6.00,
            6.01,
            6.00,
        ],
        [
            9.00,
            9.01,
            9.00,
            9.01,
            9.00,
        ],
        [
            5.00,
            5.01,
            5.00,
            5.01,
            5.00,
        ],
    ]

    targets = [
        INCREASE,
        INCREASE,
        INCREASE,
        INCREASE,
        INCREASE,
        DECREASE,
        DECREASE,
        DECREASE,
        DECREASE,
        DECREASE,
        STABLE,
        STABLE,
        STABLE,
        STABLE,
        STABLE,
    ]

    features = [
        _features(prices)
        for prices in feature_sets
    ]

    return features, targets


def test_build_training_target():
    model = PriceDirectionModel(
        stable_threshold=0.02,
    )

    assert (
        model.build_training_target(
            current_price=10.0,
            future_price=11.0,
        )
        == INCREASE
    )

    assert (
        model.build_training_target(
            current_price=10.0,
            future_price=9.0,
        )
        == DECREASE
    )

    assert (
        model.build_training_target(
            current_price=10.0,
            future_price=10.1,
        )
        == STABLE
    )


def test_build_training_target_with_invalid_current_price():
    model = PriceDirectionModel()

    assert (
        model.build_training_target(
            current_price=0.0,
            future_price=10.0,
        )
        == STABLE
    )


def test_fit_requires_equal_lengths():
    model = PriceDirectionModel()

    features = [
        _features(
            [
                8.00,
                8.10,
                8.20,
                8.30,
                8.40,
            ]
        )
    ]

    with pytest.raises(
        ValueError,
        match="equal length",
    ):
        model.fit(
            features=features,
            targets=[],
        )


def test_fit_requires_minimum_training_examples():
    model = PriceDirectionModel()

    features = [
        _features(
            [
                8.00,
                8.10,
                8.20,
                8.30,
                8.40,
            ]
        )
        for _ in range(9)
    ]

    targets = [
        INCREASE
        for _ in range(9)
    ]

    with pytest.raises(
        ValueError,
        match="At least 10 training examples",
    ):
        model.fit(
            features=features,
            targets=targets,
        )


def test_fit_requires_multiple_classes():
    model = PriceDirectionModel()

    features = [
        _features(
            [
                8.00,
                8.10,
                8.20,
                8.30,
                8.40,
            ]
        )
        for _ in range(10)
    ]

    targets = [
        INCREASE
        for _ in range(10)
    ]

    with pytest.raises(
        ValueError,
        match="at least two price-direction classes",
    ):
        model.fit(
            features=features,
            targets=targets,
        )


def test_fit_rejects_unknown_targets():
    model = PriceDirectionModel()

    features = [
        _features(
            [
                8.00,
                8.10,
                8.20,
                8.30,
                8.40,
            ]
        )
        for _ in range(10)
    ]

    targets = [
        INCREASE,
        STABLE,
        DECREASE,
        INCREASE,
        STABLE,
        DECREASE,
        INCREASE,
        STABLE,
        DECREASE,
        "UNKNOWN",
    ]

    with pytest.raises(
        ValueError,
        match="Unknown training targets",
    ):
        model.fit(
            features=features,
            targets=targets,
        )


def test_predict_requires_fitted_model():
    model = PriceDirectionModel()

    with pytest.raises(
        RuntimeError,
        match="must be fitted",
    ):
        model.predict_proba(
            _features(
                [
                    8.00,
                    8.10,
                    8.20,
                    8.30,
                    8.40,
                ]
            )
        )


def test_predict_proba_returns_valid_probability_distribution():
    features, targets = _training_data()

    model = PriceDirectionModel()

    model.fit(
        features=features,
        targets=targets,
    )

    probabilities = model.predict_proba(
        _features(
            [
                8.00,
                8.10,
                8.20,
                8.30,
                8.50,
            ]
        )
    )

    assert 0.0 <= probabilities.increase <= 1.0
    assert 0.0 <= probabilities.stable <= 1.0
    assert 0.0 <= probabilities.decrease <= 1.0

    total = (
        probabilities.increase
        + probabilities.stable
        + probabilities.decrease
    )

    assert total == pytest.approx(
        1.0,
        abs=0.001,
    )


def test_probability_dictionary_contains_all_states():
    features, targets = _training_data()

    model = PriceDirectionModel()

    model.fit(
        features=features,
        targets=targets,
    )

    probabilities = model.predict_proba(
        _features(
            [
                8.00,
                8.10,
                8.20,
                8.30,
                8.40,
            ]
        )
    )

    values = probabilities.as_dict()

    assert set(values) == {
        INCREASE,
        STABLE,
        DECREASE,
    }