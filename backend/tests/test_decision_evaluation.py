from datetime import date, timedelta

import pytest

from app.ml.forecasting import PricePoint
from app.services.decision_evaluation import (
    chronological_split,
    chronological_time_split,
    evaluate_model,
    evaluate_probabilities,
)
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
    price_series = [
        (
            [8.00, 8.10, 8.20, 8.30, 8.40],
            INCREASE,
        ),
        (
            [7.00, 7.10, 7.20, 7.30, 7.40],
            INCREASE,
        ),
        (
            [6.00, 6.10, 6.20, 6.30, 6.40],
            INCREASE,
        ),
        (
            [9.00, 9.10, 9.20, 9.30, 9.40],
            INCREASE,
        ),
        (
            [5.00, 5.10, 5.20, 5.30, 5.40],
            INCREASE,
        ),
        (
            [8.40, 8.30, 8.20, 8.10, 8.00],
            DECREASE,
        ),
        (
            [7.40, 7.30, 7.20, 7.10, 7.00],
            DECREASE,
        ),
        (
            [6.40, 6.30, 6.20, 6.10, 6.00],
            DECREASE,
        ),
        (
            [9.40, 9.30, 9.20, 9.10, 9.00],
            DECREASE,
        ),
        (
            [5.40, 5.30, 5.20, 5.10, 5.00],
            DECREASE,
        ),
        (
            [8.00, 8.01, 8.00, 8.01, 8.00],
            STABLE,
        ),
        (
            [7.00, 7.01, 7.00, 7.01, 7.00],
            STABLE,
        ),
        (
            [6.00, 6.01, 6.00, 6.01, 6.00],
            STABLE,
        ),
        (
            [9.00, 9.01, 9.00, 9.01, 9.00],
            STABLE,
        ),
        (
            [5.00, 5.01, 5.00, 5.01, 5.00],
            STABLE,
        ),
    ]

    features = [
        _features(prices)
        for prices, _ in price_series
    ]

    targets = [
        target
        for _, target in price_series
    ]

    return features, targets


def test_chronological_split_preserves_order():
    features = [
        _features(
            [8.00, 8.10, 8.20, 8.30, 8.40]
        )
        for _ in range(10)
    ]

    targets = [
        INCREASE,
        INCREASE,
        INCREASE,
        INCREASE,
        INCREASE,
        DECREASE,
        DECREASE,
        STABLE,
        STABLE,
        STABLE,
    ]

    (
        train_features,
        test_features,
        train_targets,
        test_targets,
    ) = chronological_split(
        features,
        targets,
        test_ratio=0.20,
    )

    assert len(train_features) == 8
    assert len(test_features) == 2
    assert train_targets == targets[:8]
    assert test_targets == targets[8:]


def test_chronological_split_applies_gap():
    features = [
        _features(
            [8.00, 8.10, 8.20, 8.30, 8.40]
        )
        for _ in range(20)
    ]

    targets = (
        [INCREASE] * 10
        + [DECREASE] * 6
        + [STABLE] * 4
    )

    (
        train_features,
        test_features,
        train_targets,
        test_targets,
    ) = chronological_split(
        features,
        targets,
        test_ratio=0.20,
        gap=2,
    )

    assert len(train_features) == 16
    assert len(test_features) == 2
    assert train_targets == targets[:16]
    assert test_targets == targets[18:]


def test_chronological_split_requires_equal_lengths():
    features = [
        _features(
            [8.00, 8.10, 8.20, 8.30, 8.40]
        )
    ]

    with pytest.raises(
        ValueError,
        match="equal length",
    ):
        chronological_split(
            features,
            [],
        )


def test_chronological_split_validates_ratio():
    features = [
        _features(
            [8.00, 8.10, 8.20, 8.30, 8.40]
        ),
        _features(
            [8.00, 8.10, 8.20, 8.30, 8.40]
        ),
    ]

    with pytest.raises(
        ValueError,
        match="between 0 and 1",
    ):
        chronological_split(
            features,
            [INCREASE, DECREASE],
            test_ratio=0.0,
        )


def test_chronological_split_requires_two_examples():
    features = [
        _features(
            [8.00, 8.10, 8.20, 8.30, 8.40]
        )
    ]

    with pytest.raises(
        ValueError,
        match="At least two examples",
    ):
        chronological_split(
            features,
            [INCREASE],
        )


def test_chronological_split_rejects_negative_gap():
    features = [
        _features(
            [8.00, 8.10, 8.20, 8.30, 8.40]
        ),
        _features(
            [8.00, 8.10, 8.20, 8.30, 8.40]
        ),
    ]

    with pytest.raises(
        ValueError,
        match="non-negative",
    ):
        chronological_split(
            features,
            [INCREASE, DECREASE],
            gap=-1,
        )


def test_chronological_split_rejects_gap_too_large():
    features = [
        _features(
            [8.00, 8.10, 8.20, 8.30, 8.40]
        ),
        _features(
            [8.00, 8.10, 8.20, 8.30, 8.40]
        ),
    ]

    with pytest.raises(
        ValueError,
        match="gap is too large",
    ):
        chronological_split(
            features,
            [INCREASE, DECREASE],
            gap=2,
        )


def test_chronological_time_split_uses_calendar_gap():
    prices = [
        8.00,
        8.10,
        8.20,
        8.30,
        8.40,
    ]

    features = [
        _features(prices)
        for _ in range(5)
    ]

    targets = [
        INCREASE,
        STABLE,
        DECREASE,
        INCREASE,
        STABLE,
    ]

    dates = [
        date(2026, 1, 1),
        date(2026, 1, 1),
        date(2026, 1, 2),
        date(2026, 1, 8),
        date(2026, 1, 30),
    ]

    (
        train_features,
        test_features,
        train_targets,
        test_targets,
    ) = chronological_time_split(
        features=features,
        targets=targets,
        current_dates=dates,
        test_ratio=0.40,
        gap_weeks=2,
    )

    assert len(train_features) == 3
    assert len(test_features) == 1
    assert train_targets == targets[:3]
    assert test_targets == [STABLE]


def test_chronological_time_split_requires_equal_lengths():
    features = [
        _features(
            [8.00, 8.10, 8.20, 8.30, 8.40]
        ),
        _features(
            [8.00, 8.10, 8.20, 8.30, 8.40]
        ),
    ]

    with pytest.raises(
        ValueError,
        match="equal length",
    ):
        chronological_time_split(
            features,
            [INCREASE, DECREASE],
            [date(2026, 1, 1)],
        )


def test_chronological_time_split_rejects_unsorted_dates():
    features = [
        _features(
            [8.00, 8.10, 8.20, 8.30, 8.40]
        ),
        _features(
            [8.00, 8.10, 8.20, 8.30, 8.40]
        ),
    ]

    dates = [
        date(2026, 2, 1),
        date(2026, 1, 1),
    ]

    with pytest.raises(
        ValueError,
        match="sorted chronologically",
    ):
        chronological_time_split(
            features,
            [INCREASE, DECREASE],
            dates,
        )


def test_chronological_time_split_rejects_negative_gap():
    features = [
        _features(
            [8.00, 8.10, 8.20, 8.30, 8.40]
        ),
        _features(
            [8.00, 8.10, 8.20, 8.30, 8.40]
        ),
    ]

    dates = [
        date(2026, 1, 1),
        date(2026, 1, 8),
    ]

    with pytest.raises(
        ValueError,
        match="non-negative",
    ):
        chronological_time_split(
            features,
            [INCREASE, DECREASE],
            dates,
            gap_weeks=-1,
        )


def test_chronological_time_split_rejects_gap_too_large():
    features = [
        _features(
            [8.00, 8.10, 8.20, 8.30, 8.40]
        ),
        _features(
            [8.00, 8.10, 8.20, 8.30, 8.40]
        ),
    ]

    dates = [
        date(2026, 1, 1),
        date(2026, 1, 8),
    ]

    with pytest.raises(
        ValueError,
        match="gap_weeks is too large",
    ):
        chronological_time_split(
            features,
            [INCREASE, DECREASE],
            dates,
            gap_weeks=4,
        )


def test_evaluate_model_returns_metrics():
    features, targets = _training_data()

    model = PriceDirectionModel()

    model.fit(
        features=features,
        targets=targets,
    )

    result = evaluate_model(
        model=model,
        features=features,
        targets=targets,
    )

    assert result.sample_count == 15
    assert 0.0 <= result.accuracy <= 1.0

    assert len(result.confusion_matrix) == 3

    assert all(
        len(row) == 3
        for row in result.confusion_matrix
    )

    assert set(
        result.classification_report
    ) >= {
        INCREASE,
        STABLE,
        DECREASE,
    }


def test_evaluate_model_requires_equal_lengths():
    features, _ = _training_data()

    model = PriceDirectionModel()

    with pytest.raises(
        ValueError,
        match="equal length",
    ):
        evaluate_model(
            model=model,
            features=features,
            targets=[],
        )


def test_evaluate_model_requires_examples():
    model = PriceDirectionModel()

    with pytest.raises(
        ValueError,
        match="At least one evaluation example",
    ):
        evaluate_model(
            model=model,
            features=[],
            targets=[],
        )


def test_evaluate_probabilities_returns_metrics():
    features, targets = _training_data()

    model = PriceDirectionModel()

    model.fit(
        features=features,
        targets=targets,
    )

    result = evaluate_probabilities(
        model=model,
        features=features,
        targets=targets,
    )

    assert result.sample_count == 15
    assert result.log_loss >= 0.0
    assert result.brier_score >= 0.0


def test_evaluate_probabilities_requires_equal_lengths():
    features, _ = _training_data()

    model = PriceDirectionModel()

    with pytest.raises(
        ValueError,
        match="equal length",
    ):
        evaluate_probabilities(
            model=model,
            features=features,
            targets=[],
        )


def test_evaluate_probabilities_requires_examples():
    model = PriceDirectionModel()

    with pytest.raises(
        ValueError,
        match="At least one evaluation example",
    ):
        evaluate_probabilities(
            model=model,
            features=[],
            targets=[],
        )
