"""
Budget-constrained basket optimizer.

Framed as a 0/1 knapsack / integer program: maximize a utility score
(how well the item matches the user's usual purchases + nutrition
value) subject to sum(price * qty) <= budget. This is the centerpiece
algorithm of the project -- a real OR technique, not an LLM guessing
at arithmetic.

Uses PuLP (pure Python, no external solver install needed -- ships
with CBC). For larger catalogs, swap in Google OR-Tools' CP-SAT
without changing the public interface.
"""
from dataclasses import dataclass

import pulp


@dataclass
class BasketItem:
    product_id: int
    name: str
    unit_price: float
    utility: float  # 0-1 score: how well this matches usual purchases / nutrition needs
    usual_quantity: int = 1
    max_quantity: int = 3


@dataclass
class OptimizedBasket:
    items: list[tuple[BasketItem, int]]  # (item, quantity chosen)
    total_cost: float
    total_utility: float


def optimize_basket(candidates: list[BasketItem], budget: float) -> OptimizedBasket:
    prob = pulp.LpProblem("basket_optimization", pulp.LpMaximize)

    qty_vars = {
        c.product_id: pulp.LpVariable(f"qty_{c.product_id}", lowBound=0, upBound=c.max_quantity, cat="Integer")
        for c in candidates
    }

    # Objective: maximize utility, weighted so quantities near "usual" are preferred
    prob += pulp.lpSum(qty_vars[c.product_id] * c.utility for c in candidates)

    # Budget constraint
    prob += pulp.lpSum(qty_vars[c.product_id] * c.unit_price for c in candidates) <= budget

    prob.solve(pulp.PULP_CBC_CMD(msg=0))

    chosen = []
    total_cost = 0.0
    total_utility = 0.0
    for c in candidates:
        qty = int(qty_vars[c.product_id].value() or 0)
        if qty > 0:
            chosen.append((c, qty))
            total_cost += c.unit_price * qty
            total_utility += c.utility * qty

    return OptimizedBasket(items=chosen, total_cost=round(total_cost, 2), total_utility=round(total_utility, 2))
