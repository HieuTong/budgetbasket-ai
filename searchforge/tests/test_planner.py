
import random
import unittest
from itertools import product

from searchforge import (
    BasketConstraints,
    BasketSlot,
    NoFeasibleBasketError,
    ProductCandidate,
    plan_basket_astar,
)


def exhaustive_minimum_cost(slots, constraints):
    """Return the minimum feasible cost, or None if no feasible basket exists."""
    eligible_by_slot = [
        [
            candidate
            for candidate in slot.candidates
            if not (candidate.tags & constraints.forbidden_tags)
        ]
        for slot in slots
    ]

    if any(not candidates for candidates in eligible_by_slot):
        return None

    best_cost = None

    for combination in product(*eligible_by_slot):
        cost = sum(candidate.price_cents for candidate in combination)
        protein = sum(candidate.protein_g for candidate in combination)
        fiber = sum(candidate.fiber_g for candidate in combination)

        if cost > constraints.budget_cents:
            continue
        if protein < constraints.min_protein_g:
            continue
        if fiber < constraints.min_fiber_g:
            continue

        if best_cost is None or cost < best_cost:
            best_cost = cost

    return best_cost


class AStarPlannerTests(unittest.TestCase):
    def setUp(self):
        self.basic_slots = (
            BasketSlot(
                "breakfast",
                (
                    ProductCandidate("cereal-cheap", "Budget cereal", 100, 1, 1),
                    ProductCandidate("cereal-protein", "Protein cereal", 200, 8, 5),
                ),
            ),
            BasketSlot(
                "dairy",
                (
                    ProductCandidate("milk-cheap", "Budget milk", 100, 2, 0),
                    ProductCandidate("milk-protein", "High-protein milk", 180, 5, 1),
                ),
            ),
        )

    def test_finds_lowest_price_basket_meeting_nutrition_targets(self):
        plan = plan_basket_astar(
            self.basic_slots,
            BasketConstraints(
                budget_cents=500,
                min_protein_g=12,
                min_fiber_g=2,
            ),
        )

        self.assertEqual(plan.total_price_cents, 380)
        self.assertEqual(
            {p.product_id for p in plan.selected_products},
            {"cereal-protein", "milk-protein"},
        )
        self.assertGreater(plan.generated_nodes, 0)
        self.assertGreater(plan.expanded_nodes, 0)

    def test_respects_budget(self):
        with self.assertRaises(NoFeasibleBasketError):
            plan_basket_astar(
                self.basic_slots,
                BasketConstraints(
                    budget_cents=300,
                    min_protein_g=12,
                    min_fiber_g=2,
                ),
            )

    def test_excludes_forbidden_tags(self):
        slots = (
            BasketSlot(
                "snack",
                (
                    ProductCandidate(
                        "bar-with-nuts", "Nut bar", 50, tags=frozenset({"nuts"})
                    ),
                    ProductCandidate("plain-bar", "Plain bar", 80),
                ),
            ),
        )

        plan = plan_basket_astar(
            slots,
            BasketConstraints(
                budget_cents=100,
                forbidden_tags=frozenset({"nuts"}),
            ),
        )

        self.assertEqual([p.product_id for p in plan.selected_products], ["plain-bar"])

    def test_raises_when_a_slot_has_no_eligible_candidates(self):
        slots = (
            BasketSlot(
                "snack",
                (
                    ProductCandidate(
                        "nut-bar", "Nut bar", 50, tags=frozenset({"nuts"})
                    ),
                ),
            ),
        )

        with self.assertRaises(NoFeasibleBasketError):
            plan_basket_astar(
                slots,
                BasketConstraints(
                    budget_cents=100,
                    forbidden_tags=frozenset({"nuts"}),
                ),
            )

    def test_empty_basket_is_valid_when_no_nutrition_is_required(self):
        plan = plan_basket_astar((), BasketConstraints(budget_cents=100))
        self.assertEqual(plan.total_price_cents, 0)
        self.assertEqual(plan.selected_products, ())

    def test_astar_matches_exhaustive_oracle_on_small_cases(self):
        rng = random.Random(20261009)
        possible_tags = ("nuts", "dairy")

        for case_index in range(100):
            slots = []

            for slot_index in range(rng.randint(1, 4)):
                candidates = []

                for candidate_index in range(rng.randint(1, 3)):
                    tags = frozenset(
                        rng.sample(
                            possible_tags,
                            k=rng.randint(0, len(possible_tags)),
                        )
                    )

                    candidates.append(
                        ProductCandidate(
                            product_id=(
                                f"case-{case_index}-slot-{slot_index}"
                                f"-candidate-{candidate_index}"
                            ),
                            name=f"Product {candidate_index}",
                            price_cents=rng.randint(1, 600),
                            protein_g=rng.randint(0, 12),
                            fiber_g=rng.randint(0, 5),
                            tags=tags,
                        )
                    )

                slots.append(
                    BasketSlot(f"slot-{slot_index}", tuple(candidates))
                )

            slots = tuple(slots)
            constraints = BasketConstraints(
                budget_cents=rng.randint(100, 1500),
                min_protein_g=rng.randint(0, 25),
                min_fiber_g=rng.randint(0, 10),
                forbidden_tags=frozenset(
                    rng.sample(
                        possible_tags,
                        k=rng.randint(0, len(possible_tags)),
                    )
                ),
            )

            expected_cost = exhaustive_minimum_cost(slots, constraints)

            if expected_cost is None:
                with self.assertRaises(
                    NoFeasibleBasketError,
                    msg=f"Unexpected feasible plan in case {case_index}",
                ):
                    plan_basket_astar(slots, constraints)
            else:
                plan = plan_basket_astar(slots, constraints)
                self.assertEqual(
                    plan.total_price_cents,
                    expected_cost,
                    msg=f"A* disagreed with oracle in case {case_index}",
                )
                self.assertEqual(len(plan.selected_products), len(slots))


if __name__ == "__main__":
    unittest.main()
