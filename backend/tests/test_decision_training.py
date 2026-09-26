from datetime import date, timedelta

import pytest

from app.ml.forecasting import PricePoint
from app.services.decision_training import (
    PriceTrainingBuilder,
    build_training_data,
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


def test_build_examples_creates_future_price_targets():
    history = _history(
        [
            10.00,
            10.10,
            10.20,
            10.30,
            10.40,
            10.50,
            10.60,
            10.70,
            10.80,
        ]
    )

    builder = PriceTrainingBuilder(
        lookback_weeks=4,
        forecast_horizon_weeks=4,
        stable_threshold=0.02,
    )

    examples = builder.build_examples(history)

    assert len(examples) == 1

    example = examples[0]

    assert example.features.current_price == 10.40
    assert example.target == "INCREASE"
    assert example.current_date == date(2026, 1, 29)
    assert example.future_date == date(2026, 2, 26)


def test_build_examples_detects_decrease():
    history = _history(
        [
            10.00,
            9.90,
            9.80,
            9.70,
            9.60,
            9.50,
            9.40,
            9.30,
            9.20,
        ]
    )

    builder = PriceTrainingBuilder(
        lookback_weeks=4,
        forecast_horizon_weeks=4,
    )

    examples = builder.build_examples(history)

    assert len(examples) == 1
    assert examples[0].target == "DECREASE"


def test_build_examples_detects_stable_price():
    history = _history(
        [
            10.00,
            10.01,
            10.00,
            10.01,
            10.00,
            10.01,
            10.00,
            10.01,
            10.00,
        ]
    )

    builder = PriceTrainingBuilder(
        lookback_weeks=4,
        forecast_horizon_weeks=4,
        stable_threshold=0.02,
    )

    examples = builder.build_examples(history)

    assert len(examples) == 1
    assert examples[0].target == "STABLE"


def test_multiple_examples_are_created():
    history = _history(
        [
            10.00,
            10.10,
            10.20,
            10.30,
            10.40,
            10.50,
            10.60,
            10.70,
            10.80,
            10.90,
            11.00,
        ]
    )

    builder = PriceTrainingBuilder(
        lookback_weeks=4,
        forecast_horizon_weeks=4,
    )

    examples = builder.build_examples(history)

    assert len(examples) == 3

    assert all(
        example.target == "INCREASE"
        for example in examples
    )


def test_history_is_sorted_before_building_examples():
    history = _history(
        [
            10.00,
            10.10,
            10.20,
            10.30,
            10.40,
            10.50,
            10.60,
            10.70,
            10.80,
        ]
    )

    shuffled = [
        history[8],
        history[2],
        history[5],
        history[0],
        history[7],
        history[3],
        history[1],
        history[6],
        history[4],
    ]

    builder = PriceTrainingBuilder()

    examples = builder.build_examples(shuffled)

    assert len(examples) == 1
    assert examples[0].target == "INCREASE"


def test_insufficient_history_returns_no_examples():
    history = _history(
        [
            10.00,
            10.10,
            10.20,
            10.30,
        ]
    )

    builder = PriceTrainingBuilder(
        lookback_weeks=4,
        forecast_horizon_weeks=4,
    )

    assert builder.build_examples(history) == []


def test_empty_history_returns_no_examples():
    builder = PriceTrainingBuilder()

    assert builder.build_examples([]) == []


def test_invalid_configuration_is_rejected():
    with pytest.raises(
        ValueError,
        match="lookback_weeks",
    ):
        PriceTrainingBuilder(
            lookback_weeks=0,
        )

    with pytest.raises(
        ValueError,
        match="forecast_horizon_weeks",
    ):
        PriceTrainingBuilder(
            forecast_horizon_weeks=0,
        )

    with pytest.raises(
        ValueError,
        match="stable_threshold",
    ):
        PriceTrainingBuilder(
            stable_threshold=-0.01,
        )


def test_build_training_data_returns_features_and_targets():
    history = _history(
        [
            10.00,
            10.10,
            10.20,
            10.30,
            10.40,
            10.50,
            10.60,
            10.70,
            10.80,
        ]
    )

    features, targets = build_training_data(
        history=history,
        lookback_weeks=4,
        forecast_horizon_weeks=4,
    )

    assert len(features) == 1
    assert len(targets) == 1

    assert features[0].current_price == 10.40
    assert targets[0] == "INCREASE"