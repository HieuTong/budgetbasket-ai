import pytest

from app.services.decision_model import (
    DECREASE,
    INCREASE,
    STABLE,
)
from app.services.decision_prior import (
    ProductPrior,
    build_product_prior,
)


def test_empty_history_uses_uniform_smoothed_prior():
    prior = build_product_prior([])

    assert isinstance(prior, ProductPrior)
    assert prior.increase == pytest.approx(1 / 3)
    assert prior.stable == pytest.approx(1 / 3)
    assert prior.decrease == pytest.approx(1 / 3)
    assert prior.history_count == 0


def test_prior_uses_point_in_time_history():
    prior = build_product_prior(
        [
            INCREASE,
            INCREASE,
            STABLE,
            DECREASE,
        ]
    )

    assert prior.history_count == 4
    assert prior.increase == pytest.approx(3 / 7)
    assert prior.stable == pytest.approx(2 / 7)
    assert prior.decrease == pytest.approx(2 / 7)


def test_prior_with_single_class_still_has_probability_for_all_classes():
    prior = build_product_prior(
        [
            INCREASE,
            INCREASE,
            INCREASE,
        ]
    )

    assert prior.increase == pytest.approx(4 / 6)
    assert prior.stable == pytest.approx(1 / 6)
    assert prior.decrease == pytest.approx(1 / 6)


def test_prior_rejects_non_positive_alpha():
    with pytest.raises(
        ValueError,
        match="alpha must be greater than 0",
    ):
        build_product_prior(
            [],
            alpha=0,
        )
