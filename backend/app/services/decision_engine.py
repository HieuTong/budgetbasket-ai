from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class Decision(str, Enum):
    BUY = "BUY"
    WAIT = "WAIT"
    SUBSTITUTE = "SUBSTITUTE"
    NO_ACTION = "NO_ACTION"


@dataclass(frozen=True)
class DecisionEvidence:
    """Structured evidence used by the decision engine."""

    current_price: float
    forecast_price: float | None = None
    forecast_change_percent: float | None = None
    forecast_confidence: float | None = None
    substitute_similarity: float | None = None
    substitute_savings_percent: float | None = None


@dataclass(frozen=True)
class DecisionResult:
    """Deterministic purchasing decision."""

    decision: Decision
    confidence: float
    reason: str


def make_decision(
    evidence: DecisionEvidence,
) -> DecisionResult:
    """
    Make a deterministic purchasing decision from structured evidence.

    Decision policy:

    1. Prefer a strong cheaper substitute when the substitute is
       sufficiently similar and provides meaningful savings.
    2. Otherwise, recommend waiting when the forecast indicates a
       meaningful price increase with reasonable confidence.
    3. Otherwise, recommend buying when the evidence supports the
       current price.
    4. Return NO_ACTION when there is insufficient evidence.

    The engine does not calculate forecasts or discover substitutes.
    Those are responsibilities of upstream intelligence services.
    """

    if evidence.current_price <= 0:
        return DecisionResult(
            decision=Decision.NO_ACTION,
            confidence=0.0,
            reason="Current price is unavailable or invalid.",
        )

    if (
        evidence.substitute_similarity is not None
        and evidence.substitute_savings_percent is not None
        and evidence.substitute_similarity >= 0.30
        and evidence.substitute_savings_percent >= 20.0
    ):
        confidence = min(
            0.95,
            0.50
            + 0.30 * evidence.substitute_similarity
            + 0.20 * min(
                evidence.substitute_savings_percent / 50.0,
                1.0,
            ),
        )

        return DecisionResult(
            decision=Decision.SUBSTITUTE,
            confidence=round(confidence, 2),
            reason=(
                "A sufficiently similar alternative provides "
                "meaningful price savings."
            ),
        )

    if (
        evidence.forecast_change_percent is not None
        and evidence.forecast_confidence is not None
        and evidence.forecast_change_percent >= 5.0
        and evidence.forecast_confidence >= 0.50
    ):
        confidence = min(
            0.95,
            0.50
            + 0.30 * evidence.forecast_confidence
            + 0.20 * min(
                evidence.forecast_change_percent / 20.0,
                1.0,
            ),
        )

        return DecisionResult(
            decision=Decision.WAIT,
            confidence=round(confidence, 2),
            reason=(
                "The forecast indicates a meaningful price increase "
                "with reasonable confidence."
            ),
        )

    if (
        evidence.forecast_change_percent is not None
        and evidence.forecast_confidence is not None
        and evidence.forecast_change_percent <= 0
        and evidence.forecast_confidence >= 0.50
    ):
        confidence = min(
            0.90,
            0.50
            + 0.30 * evidence.forecast_confidence
            + 0.10,
        )

        return DecisionResult(
            decision=Decision.BUY,
            confidence=round(confidence, 2),
            reason=(
                "The current price is not expected to increase "
                "meaningfully."
            ),
        )

    return DecisionResult(
        decision=Decision.NO_ACTION,
        confidence=0.0,
        reason=(
            "There is not enough reliable evidence to recommend "
            "buying, waiting, or substituting."
        ),
    )

