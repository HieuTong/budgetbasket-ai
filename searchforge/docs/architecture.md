# SearchForge architecture decision record

## Decision

Keep product retrieval and basket planning as separate modules. Use OpenSearch for document retrieval and A* for choosing a constraint-satisfying combination from a bounded candidate set.

## Why A* belongs in the planner

BM25 estimates how well a product document matches a text query. A* searches a state space using path cost (g(n)) and a heuristic estimate (h(n)) of the remaining cost. These scores have different meanings and should not be mixed into one ranking formula without a deliberate model.

For this prototype:

- **State:** the next basket slot to fill, selected candidates, accumulated price, protein, and fiber.
- **Action:** select one eligible candidate for the next slot.
- **Path cost (g(n)):** accumulated price in integer cents.
- **Heuristic (h(n)):** sum of the cheapest eligible price in every unfilled slot.
- **Goal:** every slot is filled and all budget/nutrition/exclusion constraints hold.
- **Pruning:** reject over-budget partial plans and states that cannot possibly reach the required protein or fiber even if the best remaining candidates are chosen.

The heuristic ignores nutrition constraints, so it can underestimate the true remaining cost but cannot overestimate it. With non-negative candidate prices, the heuristic is admissible and consistent. The first feasible goal removed from the priority queue is therefore a minimum-price feasible basket.

## Boundaries

- Retrieval produces candidate sets; it does not decide the complete basket.
- A* plans only over those candidates; it does not crawl or search the full catalogue.
- Nutrition constraints require reliable values in consistent units. Existing tags alone must not be treated as measured grams.
- The prototype does not yet account for store availability, package-size normalization, quantities greater than one, or multi-store purchasing.
- The planner is a separate experiment and must not replace BudgetBasket's PuLP optimizer or DecisionOS utility logic without benchmark evidence and an explicit design review.

## Evaluation plan

1. Compare A* output with exhaustive enumeration on small random instances. Every feasible instance should return the same minimum cost as the oracle.
2. Test edge cases: no eligible candidate, budget too low, impossible nutrition targets, empty basket, zero-price candidates, and ties.
3. Compare against a greedy baseline on runtime, feasibility rate, solution cost, expanded nodes, and generated nodes.
4. Compare with the existing PuLP formulation only after both solve the same formally specified problem.
5. For retrieval, separately measure Recall@k / nDCG@k and p50/p95 latency. Planner optimality is not a search-relevance metric.

## Integration sequence

1. Validate the standalone algorithm.
2. Build a read-only adapter over the existing catalogue and latest price observations.
3. Add OpenSearch ingestion and idempotent reconciliation.
4. Add a Search API orchestration layer.
5. Add telemetry and benchmarks.
6. Deploy a demo only after the local evaluation is repeatable.
