# SearchForge — Product Retrieval + A* Basket Planning

SearchForge is an isolated portfolio prototype built around Australian grocery products. It explores two different search problems:

1. **Information retrieval:** retrieve and rank relevant product documents (planned: OpenSearch BM25, filters, and optional hybrid retrieval).
2. **Constraint-aware planning:** use A* to choose one product per requested basket slot while minimizing total price and satisfying budget, nutrition, and exclusion constraints.

The first milestone implements the planning algorithm as a dependency-free Python package. It is deliberately placed in its own `searchforge/` directory and on the `feature/searchforge-astar` branch so it does not change BudgetBasket's existing optimizer, retriever, API, or DecisionOS work.

## Current scope

- Typed models for products, requested basket slots, hard constraints, and plans.
- A* planner with an admissible lower-bound heuristic.
- Pruning for budget, forbidden tags, and impossible nutrition targets.
- Node-expansion diagnostics for later algorithm comparisons.
- Unit tests for optimality on a small example and key constraints.

The nutrition fields are prototype inputs. The current catalogue's nutrition tags are not automatically equivalent to measured nutrition values; an explicit, validated data adapter is required before using real catalogue data for nutrition guarantees.

## Run locally

From the repository root:

```bash
python -m pip install -e ./searchforge
python -m unittest discover -s searchforge/tests -v
```

## Intended architecture

```text
Product catalogue / price observations
                 |
          ingestion adapter
                 |
             OpenSearch
       (BM25 + structured filters)
                 |
           Search API
                 |
       bounded candidate sets
                 |
         A* basket planner
                 |
    feasible basket + diagnostics
```

The retrieval engine and planner have separate responsibilities. OpenSearch finds relevant candidates; A* chooses a feasible combination from those candidates. A* is not intended to replace BM25.

## Next milestones

1. Add deterministic product fixtures and a brute-force oracle to verify A* optimality over many small cases.
2. Add a catalogue adapter that uses the existing product and price-observation models without changing them.
3. Add OpenSearch index mapping, idempotent indexing, and a reindex/reconciliation path.
4. Add a Search API endpoint that retrieves candidates and invokes the planner.
5. Compare A* with a greedy baseline and the existing PuLP optimizer on defined benchmark cases.
6. Add relevance, latency, and search-planner diagnostics before attempting cloud deployment.

## Design caveats

A* is appropriate here because the task is constrained combinatorial planning, not ordinary text matching. Its optimality depends on non-negative prices and an admissible heuristic. The search space can grow rapidly, so candidate sets must be bounded and performance measured. The planner should not be described as production-ready until it is tested against a brute-force oracle and representative data.
