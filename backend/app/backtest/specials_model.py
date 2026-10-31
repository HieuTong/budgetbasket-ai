"""A small, explainable model of the specials cycle, trained with a strict time split."""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import brier_score_loss, roc_auc_score
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from .data import WeeklySeries
from .features import FEATURE_NAMES, build_features, label
from .simulator import PERISHABLE, max_wait_for

MIN_HISTORY = 8


def build_dataset(series: list[WeeklySeries], start: int, end: int):
    """Examples for weeks t in [start, end) whose label window ALSO ends before `end`.

    Dropping examples whose label would peek past `end` is the embargo: without it, training
    labels would contain prices from the test period, and test results would look too good.
    """
    X, y = [], []
    for s in series:
        horizon = max_wait_for(s.category)
        perishable = s.category.lower() in PERISHABLE
        for t in range(max(start, MIN_HISTORY), end):
            if t + horizon >= end:
                break
            lab = label(s.prices, t, horizon)
            if lab is not None:
                X.append(build_features(s.prices, t, perishable))
                y.append(lab)
    return np.array(X, dtype=float), np.array(y, dtype=int)


@dataclass
class ClassificationReport:
    n: int
    base_rate: float
    auc: float | None
    brier: float
    brier_baseline: float  # Brier score of always predicting the base rate


class SpecialsModel:
    def __init__(self, C: float = 1.0):
        self.pipeline = make_pipeline(StandardScaler(), LogisticRegression(C=C, max_iter=1000))

    def fit(self, X, y) -> "SpecialsModel":
        if len(set(y)) < 2:
            raise ValueError("Training data needs both outcomes (cheaper and not cheaper)")
        self.pipeline.fit(X, y)
        return self

    def predict_proba(self, X) -> np.ndarray:
        return self.pipeline.predict_proba(X)[:, 1]

    def evaluate(self, X, y) -> ClassificationReport:
        p = self.predict_proba(X)
        base = float(y.mean())
        return ClassificationReport(
            n=len(y), base_rate=round(base, 3),
            auc=round(float(roc_auc_score(y, p)), 3) if len(set(y)) == 2 else None,
            brier=round(float(brier_score_loss(y, p)), 4),
            brier_baseline=round(float(brier_score_loss(y, np.full(len(y), base))), 4),
        )

    def coefficients(self) -> dict[str, float]:
        lr = self.pipeline[-1]
        return {n: round(float(c), 3) for n, c in zip(FEATURE_NAMES, lr.coef_[0])}


class SpecialsModelPolicy:
    """WAIT when the model's probability that the item gets cheaper soon reaches the threshold."""

    def __init__(self, model: SpecialsModel, threshold: float = 0.5, perishable_categories=PERISHABLE):
        self.model, self.threshold = model, threshold
        self.perishable_categories = perishable_categories
        self.name = f"specials_model_p{int(threshold * 100)}"
        self.category = "pantry"  # set per series by the experiment

    def decide(self, dates, prices):
        if len(prices) <= MIN_HISTORY:
            return "BUY"
        x = build_features(prices, len(prices) - 1, self.category in self.perishable_categories)
        p = float(self.model.predict_proba(np.array([x]))[0])
        return "WAIT" if p >= self.threshold else "BUY"
