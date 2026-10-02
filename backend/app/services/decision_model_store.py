from __future__ import annotations

from pathlib import Path

import joblib

from app.services.decision_model import PriceDirectionModel


def save_m1_model(
    model: PriceDirectionModel,
    path: str | Path,
) -> None:
    if not isinstance(model, PriceDirectionModel):
        raise TypeError(
            "model must be a PriceDirectionModel"
        )

    if not model._m1_fitted:
        raise RuntimeError(
            "M1 model must be fitted before saving"
        )

    destination = Path(path)
    destination.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    joblib.dump(
        model,
        destination,
    )


def load_m1_model(
    path: str | Path,
) -> PriceDirectionModel:
    source = Path(path)

    if not source.exists():
        raise FileNotFoundError(
            f"M1 model artifact not found: {source}"
        )

    model = joblib.load(source)

    if not isinstance(model, PriceDirectionModel):
        raise TypeError(
            "M1 model artifact does not contain "
            "a PriceDirectionModel"
        )

    if not model._m1_fitted:
        raise RuntimeError(
            "Loaded PriceDirectionModel does not "
            "contain a fitted M1 model"
        )

    return model