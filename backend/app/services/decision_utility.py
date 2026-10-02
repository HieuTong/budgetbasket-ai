from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from app.services.decision_model import PriceProbability


class Action(str, Enum):
    BUY = "BUY"
    WAIT = "WAIT"
    SUBSTITUTE = "SUBSTITUTE"


@dataclass(frozen=True)
class UtilityContext:
    """
    Economic context used to calculate action consequences.
    """

    current_price: float
    forecast_price: float | None = None
    substitute_price: float | None = None


@dataclass(frozen=True)
class ExpectedUtility:
    action: Action
    value: float


@dataclass(frozen=True)
class UtilityDecision:
    action: Action
    expected_utilities: dict[str, float]


def _utility(
    action: Action,
    state: str,
    context: UtilityContext,
) -> float:
    """
    Estimate the consequence of an action under a future price state.

    Utilities are expressed in dollars relative to buying the product
    at the current price.

    This is intentionally transparent for the Phase 7 MVP.
    """

    current = context.current_price

    if current <= 0:
        return 0.0

    forecast = (
        context.forecast_price
        if context.forecast_price is not None
        and context.forecast_price > 0
        else current
    )

    substitute = (
        context.substitute_price
        if context.substitute_price is not None
        and context.substitute_price > 0
        else None
    )

    if action == Action.BUY:
        if state == "INCREASE":
            return 0.0

        if state == "STABLE":
            return 0.0

        if state == "DECREASE":
            return -(current - forecast)

    if action == Action.WAIT:
        if state == "INCREASE":
            return max(
                forecast - current,
                0.0,
            )

        if state == "STABLE":
            return 0.0

        if state == "DECREASE":
            return min(
                forecast - current,
                0.0,
            )

    if action == Action.SUBSTITUTE:
        if substitute is None:
            return 0.0

        savings = current - substitute

        if state == "INCREASE":
            return savings

        if state == "STABLE":
            return savings

        if state == "DECREASE":
            return savings

    return 0.0


def expected_utility(
    action: Action,
    probabilities: PriceProbability,
    context: UtilityContext,
) -> float:
    """
    Calculate:

        EU(action) = sum P(state) * U(action, state)
    """
    return (
        probabilities.increase
        * _utility(
            action,
            "INCREASE",
            context,
        )
        + probabilities.stable
        * _utility(
            action,
            "STABLE",
            context,
        )
        + probabilities.decrease
        * _utility(
            action,
            "DECREASE",
            context,
        )
    )


def choose_action(
    probabilities: PriceProbability,
    context: UtilityContext,
) -> UtilityDecision:
    """
    Select the action with the greatest expected utility.
    """

    utilities = {
        action.value: round(
            expected_utility(
                action,
                probabilities,
                context,
            ),
            4,
        )
        for action in Action
    }

    action = max(
        Action,
        key=lambda candidate: utilities[
            candidate.value
        ],
    )

    return UtilityDecision(
        action=action,
        expected_utilities=utilities,
    )