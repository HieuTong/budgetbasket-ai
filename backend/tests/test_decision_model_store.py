from datetime import date, timedelta
from pathlib import Path

import joblib
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
from app.services.decision_model_store import (
    load_m1_model,
    save_m1_model,
)
from app.services.decision_prior import (
    build_product_prior,
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

    return features, targets


def _fit_m1_model() -> PriceDirectionModel:
    features, targets = _training_data()

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


def test_save_m1_model_creates_artifact(
    tmp_path: Path,
):
    model = _fit_m1_model()

    artifact_path = (
        tmp_path
        / "models"
        / "decision_m1.joblib"
    )

    save_m1_model(
        model=model,
        path=artifact_path,
    )

    assert artifact_path.exists()
    assert artifact_path.is_file()


def test_save_m1_model_requires_fitted_m1_model(
    tmp_path: Path,
):
    model = PriceDirectionModel()

    artifact_path = (
        tmp_path
        / "decision_m1.joblib"
    )

    with pytest.raises(
        RuntimeError,
        match="M1 model must be fitted",
    ):
        save_m1_model(
            model=model,
            path=artifact_path,
        )


def test_save_m1_model_rejects_invalid_model(
    tmp_path: Path,
):
    artifact_path = (
        tmp_path
        / "decision_m1.joblib"
    )

    with pytest.raises(
        TypeError,
        match="PriceDirectionModel",
    ):
        save_m1_model(
            model="not a model",
            path=artifact_path,
        )


def test_load_m1_model_requires_existing_artifact(
    tmp_path: Path,
):
    artifact_path = (
        tmp_path
        / "missing.joblib"
    )

    with pytest.raises(
        FileNotFoundError,
        match="M1 model artifact not found",
    ):
        load_m1_model(artifact_path)


def test_load_m1_model_round_trip(
    tmp_path: Path,
):
    model = _fit_m1_model()

    artifact_path = (
        tmp_path
        / "models"
        / "decision_m1.joblib"
    )

    save_m1_model(
        model=model,
        path=artifact_path,
    )

    loaded = load_m1_model(
        artifact_path
    )

    assert isinstance(
        loaded,
        PriceDirectionModel,
    )

    assert loaded._m1_fitted is True

    features = _features(
        [
            8.00,
            8.10,
            8.20,
            8.30,
            8.50,
        ]
    )

    prior = build_product_prior(
        [
            INCREASE,
            STABLE,
            DECREASE,
        ]
    )

    original_probability = (
        model.predict_proba_m1(
            features,
            prior,
        )
    )

    loaded_probability = (
        loaded.predict_proba_m1(
            features,
            prior,
        )
    )

    assert (
        loaded_probability
        == original_probability
    )


def test_load_m1_model_rejects_wrong_artifact(
    tmp_path: Path,
):
    artifact_path = (
        tmp_path
        / "wrong.joblib"
    )

    joblib.dump(
        {"not": "a model"},
        artifact_path,
    )

    with pytest.raises(
        TypeError,
        match="does not contain a PriceDirectionModel",
    ):
        load_m1_model(artifact_path)
