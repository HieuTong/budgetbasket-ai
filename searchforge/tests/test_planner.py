import unittest

from searchforge import (
    BasketConstraints,
    BasketSlot,
    NoFeasibleBasketError,
    ProductCandidate,
    plan_basket_astar,
)


class AStarPlannerTests(unittest.TestCase):
    def setUp(self) -> None:
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

    def test_finds_lowest_price_basket_meeting_nutrition_targets(self) -> None:
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
            {product.product_id for product in plan.selected_products},
            {"cereal-protein", "milk-protein"},
        )
        self.assertGreater(plan.generated_nodes, 0)
        self.assertGreater(plan.expanded_nodes, 0)

    def test_respects_budget(self) -> None:
        with self.assertRaises(NoFeasibleBasketError):
            plan_basket_astar(
                self.basic_slots,
                BasketConstraints(
                    budget_cents=300,
                    min_protein_g=12,
                    min_fiber_g=2,
                ),
            )

    def test_excludes_forbidden_tags(self) -> None:
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
            BasketConstraints(budget_cents=100, forbidden_tags=frozenset({"nuts"})),
        )

        self.assertEqual([p.product_id for p in plan.selected_products], ["plain-bar"])

    def test_raises_when_a_slot_has_no_eligible_candidates(self) -> None:
        slots = (
            BasketSlot(
                "snack",
                (ProductCandidate("nut-bar", "Nut bar", 50, tags=frozenset({"nuts"})),),
            ),
        )
        with self.assertRaises(NoFeasibleBasketError):
            plan_basket_astar(
                slots,
                BasketConstraints(budget_cents=100, forbidden_tags=frozenset({"nuts"})),
            )

    def test_empty_basket_is_valid_when_no_nutrition_is_required(self) -> None:
        plan = plan_basket_astar((), BasketConstraints(budget_cents=100))
        self.assertEqual(plan.total_price_cents, 0)
        self.assertEqual(plan.selected_products, ())


if __name__ == "__main__":
    unittest.main()
