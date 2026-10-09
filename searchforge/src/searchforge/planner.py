"""A* search for the lowest-cost basket satisfying hard constraints.

The heuristic sums the cheapest eligible candidate price in every unfilled
slot. It deliberately ignores nutrition constraints, making it an admissible
lower bound on the remaining price. The first feasible goal popped is therefore
a minimum-price feasible basket, provided candidate prices are non-negative.
"""

from __future__ import annotations

import heapq
from itertools import count
from typing import Iterable

from searchforge.models import (
    BasketConstraints,
    BasketPlan,
    BasketSlot,
    ProductCandidate,
)


class NoFeasibleBasketError(ValueError):
    """Raised when no basket satisfies the supplied constraints."""


def plan_basket_astar(
    slots: Iterable[BasketSlot],
    constraints: BasketConstraints,
) -> BasketPlan:
    """Find a minimum-price feasible basket with A*.

    Exactly one candidate is selected for each slot. Products carrying any
    forbidden tag are excluded. The total price must stay within the budget,
    and the completed basket must meet the minimum protein/fiber requirements.

    This planner operates on a bounded candidate set; retrieval/ranking of
    candidates belongs to the search service, not this algorithm.
    """

    slot_list = tuple(slots)
    eligible_by_slot: list[tuple[ProductCandidate, ...]] = []

    for slot in slot_list:
        eligible = tuple(
            sorted(
                (
                    candidate
                    for candidate in slot.candidates
                    if not (candidate.tags & constraints.forbidden_tags)
                ),
                key=lambda candidate: (candidate.price_cents, candidate.product_id),
            )
        )
        if not eligible:
            raise NoFeasibleBasketError(
                f"Slot {slot.slot_id!r} has no eligible candidates"
            )
        eligible_by_slot.append(eligible)

    slot_count = len(eligible_by_slot)

    def cheapest_remaining(start: int) -> int:
        return sum(
            min(candidate.price_cents for candidate in eligible_by_slot[index])
            for index in range(start, slot_count)
        )

    def maximum_remaining_nutrition(start: int) -> tuple[float, float]:
        max_protein = sum(
            max(candidate.protein_g for candidate in eligible_by_slot[index])
            for index in range(start, slot_count)
        )
        max_fiber = sum(
            max(candidate.fiber_g for candidate in eligible_by_slot[index])
            for index in range(start, slot_count)
        )
        return max_protein, max_fiber

    initial_lower_bound = cheapest_remaining(0)
    if initial_lower_bound > constraints.budget_cents:
        raise NoFeasibleBasketError("The minimum possible price exceeds the budget")

    # Entries: (f = g + h, g, stable tie-breaker, next slot index,
    #           selected products, protein total, fiber total).
    tie_breaker = count()
    frontier: list[tuple[int, int, int, int, tuple[ProductCandidate, ...], float, float]] = [
        (initial_lower_bound, 0, next(tie_breaker), 0, (), 0.0, 0.0)
    ]
    expanded_nodes = 0
    generated_nodes = 1

    while frontier:
        _, cost_cents, _, slot_index, selected, protein_g, fiber_g = heapq.heappop(
            frontier
        )
        expanded_nodes += 1

        if slot_index == slot_count:
            if (
                protein_g >= constraints.min_protein_g
                and fiber_g >= constraints.min_fiber_g
            ):
                return BasketPlan(
                    selected_products=selected,
                    total_price_cents=cost_cents,
                    total_protein_g=protein_g,
                    total_fiber_g=fiber_g,
                    expanded_nodes=expanded_nodes,
                    generated_nodes=generated_nodes,
                )
            continue

        remaining_max_protein, remaining_max_fiber = maximum_remaining_nutrition(
            slot_index
        )
        if protein_g + remaining_max_protein < constraints.min_protein_g:
            continue
        if fiber_g + remaining_max_fiber < constraints.min_fiber_g:
            continue

        for candidate in eligible_by_slot[slot_index]:
            next_cost = cost_cents + candidate.price_cents
            if next_cost > constraints.budget_cents:
                continue

            next_protein = protein_g + candidate.protein_g
            next_fiber = fiber_g + candidate.fiber_g
            next_index = slot_index + 1
            lower_bound = next_cost + cheapest_remaining(next_index)

            if lower_bound > constraints.budget_cents:
                continue

            max_protein, max_fiber = maximum_remaining_nutrition(next_index)
            if next_protein + max_protein < constraints.min_protein_g:
                continue
            if next_fiber + max_fiber < constraints.min_fiber_g:
                continue

            heapq.heappush(
                frontier,
                (
                    lower_bound,
                    next_cost,
                    next(tie_breaker),
                    next_index,
                    selected + (candidate,),
                    next_protein,
                    next_fiber,
                ),
            )
            generated_nodes += 1

    raise NoFeasibleBasketError("No basket satisfies all supplied constraints")
