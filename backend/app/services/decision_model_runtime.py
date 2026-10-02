from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from app.services.decision_model import PriceDirectionModel
from app.services.decision_model_store import load_m1_model


DEFAULT_M1_MODEL_PATH = Path(
    "data/models/decision_m1.joblib"
)


@lru_cache(maxsize=1)
def get_m1_model(
    path: str = str(DEFAULT_M1_MODEL_PATH),
) -> PriceDirectionModel:
    model = load_m1_model(
        Path(path)
    )

    return model
