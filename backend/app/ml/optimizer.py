from dataclasses import dataclass

import pulp


@dataclass
class BasketItem:
    product_id: int
    name: str
    unit_price: float
    utility: float
    usual_quantity: int = 1
    max_quantity: int = 3


@dataclass
class OptimizedBasket:
    items: list[tuple[BasketItem, int]]
    total_cost: float
    total_utility: float


def optimize_basket(
    candidates: list[BasketItem],
    budget: float,
    max_distinct_products: int | None = None,
) -> OptimizedBasket:
    prob = pulp.LpProblem(
        "basket_optimization",
        pulp.LpMaximize,
    )

    qty_vars = {
        c.product_id: pulp.LpVariable(
            f"qty_{c.product_id}",
            lowBound=0,
            upBound=c.max_quantity,
            cat="Integer",
        )
        for c in candidates
    }

    selected_vars = {}

    if max_distinct_products is not None:
        selected_vars = {
            c.product_id: pulp.LpVariable(
                f"selected_{c.product_id}",
                cat="Binary",
            )
            for c in candidates
        }

        for c in candidates:
            prob += (
                qty_vars[c.product_id]
                <= c.max_quantity
                * selected_vars[c.product_id]
            )

            prob += (
                qty_vars[c.product_id]
                >= selected_vars[c.product_id]
            )

        prob += pulp.lpSum(
            selected_vars[c.product_id]
            for c in candidates
        ) <= max_distinct_products

    prob += pulp.lpSum(
        qty_vars[c.product_id] * c.utility
        for c in candidates
    )

    prob += pulp.lpSum(
        qty_vars[c.product_id] * c.unit_price
        for c in candidates
    ) <= budget

    prob.solve(
        pulp.PULP_CBC_CMD(msg=0)
    )

    chosen = []
    total_cost = 0.0
    total_utility = 0.0

    for c in candidates:
        qty = int(
            qty_vars[c.product_id].value() or 0
        )

        if qty > 0:
            chosen.append(
                (c, qty)
            )

            total_cost += (
                c.unit_price * qty
            )

            total_utility += (
                c.utility * qty
            )

    return OptimizedBasket(
        items=chosen,
        total_cost=round(total_cost, 2),
        total_utility=round(total_utility, 2),
    )
