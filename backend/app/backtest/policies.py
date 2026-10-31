"""BUY/WAIT policies. Every policy sees only prices up to the current week: no look-ahead."""
from __future__ import annotations

from datetime import date
from typing import Protocol

from app.ml.forecasting import PricePoint, price_trend
from app.services.decision_engine import Decision, DecisionEvidence, make_decision


class Policy(Protocol):
    name: str

    def decide(self, dates: list[date], prices: list[float]) -> str:
        """Return "BUY" or "WAIT" given history up to and including the current week."""


class AlwaysBuy:
    name = "always_buy"

    def decide(self, dates, prices):
        return "BUY"


class RollingLowHeuristic:
    """Simple non-ML baseline: buy if today is within `tolerance` of the recent low, else wait."""

    def __init__(self, window: int = 8, tolerance: float = 0.05):
        self.window, self.tolerance = window, tolerance
        self.name = f"rolling_low_{window}w"

    def decide(self, dates, prices):
        recent = prices[-self.window:]
        return "BUY" if prices[-1] <= min(recent) * (1 + self.tolerance) else "WAIT"


class DecisionEnginePolicy:
    """The production path: linear price_trend forecast feeding app.services.decision_engine.

    SUBSTITUTE and NO_ACTION are treated as BUY, because the backtest only models timing.
    """

    name = "decision_engine"

    def __init__(self, horizon_weeks: int = 4):
        self.horizon_weeks = horizon_weeks

    def _forecast(self, dates, prices) -> dict:
        history = [PricePoint(date=d, unit_price=p) for d, p in zip(dates, prices)]
        return price_trend(history=history, forecast_horizon_weeks=self.horizon_weeks)

    def decide(self, dates, prices):
        f = self._forecast(dates, prices)
        result = make_decision(DecisionEvidence(
            current_price=prices[-1],
            forecast_price=f.get("forecast_price"),
            forecast_change_percent=f.get("forecast_change_percent"),
            forecast_confidence=f.get("confidence"),
        ))
        return "WAIT" if result.decision == Decision.WAIT else "BUY"


class DirectionCheckedEnginePolicy(DecisionEnginePolicy):
    """Same forecast, but waits only when the price is expected to FALL (change <= -5%, confidence >= 0.5).

    Exists to test whether the production rule's direction is right.
    """

    name = "engine_direction_checked"

    def decide(self, dates, prices):
        f = self._forecast(dates, prices)
        change, conf = f.get("forecast_change_percent"), f.get("confidence") or 0.0
        return "WAIT" if change is not None and change <= -5.0 and conf >= 0.5 else "BUY"
