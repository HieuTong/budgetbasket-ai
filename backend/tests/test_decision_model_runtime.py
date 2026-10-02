from datetime import date, timedelta
from pathlib import Path

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
from app.services.decision_model_runtime import (
    get_m1_model,
)
from app.services.decision_model_store import (
    save_m1_model,
)
from app.services.decision_prior import (
    build_product_prior,
)


def _features(
    prices: list[float],
):
    history = [
        PricePoint(
            date=date(2026, 1, 1)
            + timedelta(weeks=index),
            unit_price=price,
            transaction_count=1,
        )
        for index, price in enumerate(prices)
    ]

    features = build_price_features(
        history
    )

    assert features is not None

    return features


def _fit_model() -> PriceDirectionModel:
    feature_sets = [
        [8.00, 8.10, 8.20, 8.30, 8.40],
        [7.00, 7.10, 7.20, 7.30, 7.40],
        [6.00, 6.10, 6.20, 6.30, 6.40],
        [9.00, 9.10, 9.20, 9.30, 9.40],
        [5.00, 5.10, 5.20, 5.30, 5.40],
        [8.40, 8.30, 8.20, 8.10, 8.00],
        [7.40, 7.30, 7.20, 7.10, 7.00],
        [6.40, 6.30, 6.20, 6.10, 6.00],
        [9.40, 9.30, 9.20, 9.10, 9.00],
        [5.40, 5.30, 5.20, 5.10, 5.00],
        [8.00, 8.01, 8.00, 8.01, 8.00],
        [7.00, 7.01, 7.00, 7.01, 7.00],
        [6.00, 6.01, 6.00, 6.01, 6.00],
        [9.00, 9.01, 9.00, 9.01, 9.00],
        [5.00, 5.01, 5.00, 5.01, 5.00],
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

    priors = [
        build_product_prior(
            [
                INCREASE,
                STABLE,
                DECREASE,
            ]
        )
        for _ in features
    ]

    model = PriceDirectionModel()

    model.fit_m1(
        features=features,
        priors=priors,
        targets=targets,
    )

    return model


def test_get_m1_model_loads_saved_model(
    tmp_path: Path,
):
    model = _fit_model()

    artifact_path = (
        tmp_path
        / "decision_m1.joblib"
    )

    save_m1_model(
        model=model,
        path=artifact_path,
    )

    get_m1_model.cache_clear()

    loaded = get_m1_model(
        str(artifact_path)
    )

    assert isinstance(
        loaded,
        PriceDirectionModel,
    )

    assert loaded._m1_fitted is True


def test_get_m1_model_caches_model(
    tmp_path: Path,
):
    model = _fit_model()

    artifact_path = (
        tmp_path
        / "decision_m1.joblib"
    )

    save_m1_model(
        model=model,
        path=artifact_path,
    )

    get_m1_model.cache_clear()

    first = get_m1_model(
        str(artifact_path)
    )

    artifact_path.unlink()

    second = get_m1_model(
        str(artifact_path)
    )

    assert first is second


def test_get_m1_model_raises_for_missing_artifact(
    tmp_path: Path,
):
    get_m1_model.cache_clear()

    missing_path = (
        tmp_path
        / "missing.joblib"
    )

    with pytest.raises(
        FileNotFoundError,
        match="M1 model artifact not found",
    ):
        get_m1_model(
            str(missing_path)
        )
