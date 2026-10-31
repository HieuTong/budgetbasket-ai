# BudgetBasket AI

A cost-of-living optimizer for Australian households: given your usual purchases and a budget, it builds a shopping basket that stays close to your habits while cutting cost — using classical ML, search and retrieval, retrieval-augmented generation, and an agentic tool-calling layer, not just a single LLM prompt.

**Live Demo:** https://budgetbasket.tech  
**GitHub:** https://github.com/HieuTong/budgetbasket-ai

## Results at a glance

| Question | Result | How to reproduce |
|---|---|---|
| Does the BUY/WAIT advice save money? | The original engine saved **0%**. A dedicated specials model saves **11.4%** versus always buying (95% interval 8.9% to 14.1%), similar to a simple "buy near the recent low" rule (10.3%), while asking households to wait about half as often (44% vs 76% of purchases) and backfiring less than half as often (15% vs 34% of waits). | `python scripts/run_specials_experiment.py --synthetic` |
| Does the agent use its tools correctly? | **10 of 10** evaluation cases passed with **0** budget violations, including a prompt-injection attempt it safely refused. | `python scripts/run_agent_eval.py` |
| Is it fast enough? | Median **4.1 s**, p95 **10.4 s** per request (p95 was 76.8 s before adding timeouts and retries), about 1,640 tokens per request on `gemini-3.1-flash-lite`. | Traces from the evaluation run |

> The savings results use **synthetic** price data generated with regular specials cycles, which flatters a cycle-aware model. They show the method works end to end; real Australian price data is the next step (see Known limitations).

## What the evaluation uncovered, and what changed

1. **The decision engine never saved money.** A backtest that replays price history without look-ahead showed it behaved exactly like "always buy". There were two stacked causes:
   - The WAIT rule was **inverted**: it waited when prices were expected to *rise*. Fixed, with a regression test.
   - The linear forecast's confidence (R²) was almost always near zero on specials-driven prices (median 0.01), so the engine rarely acted at all. To address this, a separate model predicts whether an item will be at least 10% cheaper within the household's waiting window. It has been built and evaluated in the backtest; connecting it to the live app is the next step.
2. **The new model is not claimed to save more than the simple rule.** The difference is +1.2 points, but its 95% interval (−0.2 to +2.5) includes zero. Its real advantage is behaviour: fewer waits and fewer waits that backfire.
3. **The agent evaluation tested the wrong thing at first.** A "failed" injection case was the agent safely refusing to invent prices, so the check now tests the property that matters (no invented prices) rather than one specific behaviour. Random 18 to 77 second API stalls led to per-call timeouts with retry. Disabling the model's thinking did not reduce latency in a measured comparison, so the default was kept.

## How decisions stay trustworthy

- **Deterministic decisions:** the optimiser and models make every decision; the LLM routes requests and explains results but never computes prices or totals.
- **No invented prices:** enforced in the system prompt and checked by the agent evaluation.
- **Budget safety:** a property test checks the optimiser never exceeds the budget across 150 random baskets on every push, and the live evaluation gate tolerates zero budget violations.
- **Traceability:** every agent request records each model call and tool call with arguments, latency and tokens.
- **Honest evaluation:** time-based splits with an embargo, thresholds tuned only on training data, and bootstrap intervals resampled by product.

## Reproduce the evaluations

```bash
cd backend
python -m pytest -q                                   # full suite, also run in CI on every push
python scripts/run_backtest.py --synthetic            # BUY/WAIT policies vs an oracle
python scripts/run_specials_experiment.py --synthetic # specials model with 95% intervals
python scripts/run_agent_eval.py --json-out agent_eval.json  # live agent evaluation (needs GEMINI_API_KEY)
```

## Known limitations

- **Synthetic price data** in the backtest. Real observations (via `open_prices_client.py` or a public Australian price dataset) are needed before any savings claim.
- **The chat route does not yet pass the user's candidate products to the optimiser**, so basket optimisation through the live chat returns an empty basket. The agent evaluation supplies candidates directly, which is why it did not catch this; an end-to-end test through the API route is planned.
- **The agent evaluation uses stubbed database tools** (the optimiser is real) and has only 10 cases, so one case moves the pass rate by 10 points.

## Why this project

Grocery prices in Australia have risen sharply, and most "AI shopping" demos are thin wrappers around a chat prompt. This project is built to show the opposite: a **real optimization algorithm** at the core, with search, ML, and LLM components layered around it where they are the right tool — not used everywhere for effect.

The project explores several practical engineering problems:

- Retrieving relevant grocery products, including misspelled queries.
- Combining search results with structured product and price data.
- Evaluating retrieval quality and latency through repeatable benchmarks.
- Optimizing a basket under a budget constraint.
- Using an agent layer to coordinate specialized tools rather than asking an LLM to perform every operation itself.

## Architecture

```text
                         ┌─────────────────┐
                         │    Next.js UI    │
                         └────────┬────────┘
                                  │
                         ┌────────▼────────┐
                         │ FastAPI Backend  │
                         └────┬────────┬───┘
                              │        │
                 ┌────────────┘        └─────────────┐
                 │                                   │
        ┌────────▼────────┐                 ┌────────▼────────┐
        │ Search & Catalog │                 │   Agent Layer    │
        │                  │                 │                  │
        │ OpenSearch       │                 │ Tool-calling loop│
        │ PostgreSQL       │                 │ Optimizer        │
        │ Product hydration│                 │ Similarity       │
        │ Ranking & prices │                 │ RAG              │
        └──────────────────┘                 └────────┬─────────┘
                                                      │
                                            ┌─────────▼─────────┐
                                            │   RAG Retriever    │
                                            │ FAISS + fallback   │
                                            └───────────────────┘

        Classical ML:
        - Product similarity
        - Price forecasting
        - Budget optimization
```

The diagram shows the main logical components. The exact runtime connections depend on the configured application and deployment environment.

## Search Engineering

BudgetBasket includes an OpenSearch-based product retrieval path integrated with a PostgreSQL product catalog.

The search workflow separates retrieval from downstream processing:

1. **Candidate retrieval:** OpenSearch retrieves candidate grocery products for a query.
2. **Product hydration:** PostgreSQL supplies structured catalog information.
3. **Domain-specific ranking:** Grocery-aware rules help order candidate products.
4. **Price enrichment:** Product records are enriched with available price information.
5. **Evaluation:** Search behaviour is measured against the existing PostgreSQL-based search path.

### Search engineering work

- Integrated OpenSearch retrieval with PostgreSQL catalog records.
- Implemented fuzzy product search to handle misspellings.
- Applied grocery-specific ranking rules.
- Evaluated retrieval behaviour across six grocery queries.
- Built a repeatable benchmark comparing PostgreSQL search and OpenSearch.
- Investigated latency, relevance, empty results, errors, and fallback events.
- Identified remaining retrieval-quality gaps instead of assuming the newer implementation was always better.

### Search benchmark

The benchmark covered **360 measured requests across six grocery queries**.

| Measurement                | Result                                                                      |
| -------------------------- | --------------------------------------------------------------------------- |
| Total measured requests    | 360                                                                         |
| Query scenarios            | 6                                                                           |
| Observed errors            | 0                                                                           |
| Detected fallback events   | 0                                                                           |
| Misspelling test           | OpenSearch returned results for `chiken` in all 30 measured runs            |
| PostgreSQL comparison      | The legacy PostgreSQL search returned no results for `chiken` in those runs |
| Known relevance limitation | Oat-milk retrieval still needs improvement                                  |

The benchmark tracks:

- Median latency
- p95 latency
- Heuristic Precision@5
- Empty-result responses
- Errors
- Fallback events

The results are specific to the tested queries and environment. They do not establish that OpenSearch is universally faster or more relevant than PostgreSQL.

Search quality and latency need to be considered together: a fast response is not useful if the returned products do not match the user's intent.

## Why Gemini, not OpenAI

Google's Gemini API was selected for the LLM and embedding workflows based on the project's cost constraints and available API access.

Function calling is implemented through an explicit tool-calling loop, using JSON-schema tool declarations and parsed function-call responses, rather than relying entirely on automatic SDK orchestration. This keeps the agent's control flow explicit.

See `app/agent/agent.py` for the implementation.

API pricing, quotas, and free-tier availability can change. Check the provider's current terms before relying on a particular quota or cost assumption.

## Why an LP solver, not just an LLM

The budget-fitting problem is a constrained optimization problem. BudgetBasket models it using integer linear programming through PuLP and the CBC solver.

The optimizer maximizes a utility score subject to the budget constraint and the configured product-selection rules. This makes the mathematical constraints explicit and testable.

An LLM asked to perform the arithmetic directly can produce a basket that exceeds the budget or uses the budget inefficiently. Instead, the agent layer calls the optimizer as a specialized tool.

The distinction is deliberate:

- **ML and retrieval** help estimate relevance, similarity, and other useful signals.
- **The optimizer** selects a basket under explicit constraints.
- **The agent** coordinates tools and communicates the result.

## Components

| Layer                      | Technique                                           | File                                   |
| -------------------------- | --------------------------------------------------- | -------------------------------------- |
| Search and catalog         | OpenSearch retrieval and PostgreSQL product records | Search integration and catalog modules |
| Similarity and substitutes | TF-IDF and cosine similarity                        | `app/ml/similarity.py`                 |
| Price trend                | Linear regression on price history                  | `app/ml/forecasting.py`                |
| Budget optimization        | Integer linear programming using PuLP               | `app/ml/optimizer.py`                  |
| RAG                        | FAISS, Gemini embeddings, keyword fallback          | `app/rag/retriever.py`                 |
| Agent                      | Explicit tool-calling loop                          | `app/agent/agent.py`                   |

## Data

Two data sources are used deliberately for different purposes.

### External price data

`app/integrations/open_prices_client.py` provides a client for the [Open Food Facts Open Prices API](https://prices.openfoodfacts.org), an open, community-sourced grocery price database with Australian entries.

The client requires outbound internet access. It is not wired into the seed pipeline by default, so its existence should not be interpreted as evidence that the live demo continuously retrieves current prices from the API.

### Seed catalog and price history

`seed/products_seed.csv` and `seed/generate_price_history.py` provide 55 common Australian grocery items with indicative unit prices and generated historical price data.

The seed data makes the project runnable without depending on external API availability. Prices are indicative rather than guaranteed live retail prices, and generated history is not a substitute for observed transaction or retailer data.

The price-history assumptions are informed by patterns discussed in the [Australian grocery price database](https://github.com/tjhowse/aus_grocery_price_database).

### Load seed data

```bash
cd backend
python -m seed.load_seed_data
```

### Known forecasting limitation

The linear-regression price forecaster in `app/ml/forecasting.py` can average out short-term cyclical price movements instead of identifying them. For example, a cyclical item such as bananas may be classified as stable with low confidence.

Seasonal decomposition or a Fourier feature could help model such patterns. The specials-timing model in `app/backtest/specials_model.py` takes a different route: instead of forecasting the price line, it predicts whether an item will be at least 10% cheaper within the household's waiting window.

## Running locally

### Prerequisites

- Python compatible with the project's configured environment
- PostgreSQL
- A Gemini API key for features that use Gemini
- OpenSearch if you want to run and test the OpenSearch search path

### Setup

```bash
cd backend

cp .env.example .env
```

Configure the required environment variables in `.env`, including `DATABASE_URL` and `GEMINI_API_KEY` where applicable. Configure the OpenSearch endpoint and credentials according to the project's search integration.

Install dependencies:

```bash
pip install -r requirements.txt
```

Start the API:

```bash
uvicorn app.main:app --reload
```

Visit the interactive API documentation:

http://localhost:8000/docs

The API, database, and OpenSearch service must be configured and reachable for any features that depend on them. The exact setup may differ from the hosted demo.

## Deployment

The project uses separate services for the application and its supporting infrastructure.

- **Backend:** FastAPI, containerized using `backend/Dockerfile` and deployed to Render.
- **Database:** PostgreSQL hosted on Supabase.
- **Frontend:** Next.js hosted on Vercel.
- **Search infrastructure:** OpenSearch deployed on an Azure Linux virtual machine using Docker.
- **CI:** GitHub Actions runs the full pytest suite against a PostgreSQL service, then builds the Docker image. A separate weekly workflow runs the live agent evaluation and fails on any budget violation.

See `DEPLOYMENT.md` for the backend deployment walkthrough.

The OpenSearch Azure VM is a separate search-infrastructure deployment. Do not assume that the public demo uses that instance unless the backend's configured endpoint confirms the connection.

For security, do not expose OpenSearch directly to the public internet. Restrict access to trusted services, protect credentials, and use appropriate network rules.

## Testing and Evaluation

The project uses automated checks and targeted evaluation to improve correctness and reliability.

The full test suite runs on every push and pull request. Beyond unit tests, three evaluations are described in Results at a glance: a decision backtest, the specials-model experiment with bootstrap intervals, and the agent evaluation with its release gate.

For search evaluation, the benchmark compares the PostgreSQL-based search path with OpenSearch under the same measured query scenarios.

The evaluation considers both performance and retrieval quality rather than relying on a single latency number.

Useful next steps include:

- Add regression tests for misspelled product queries.
- Expand the benchmark to cover more product categories and query variations.
- Add relevance judgments to complement heuristic Precision@5.
- Measure latency under concurrent load.
- Test failure handling when OpenSearch is unavailable.
- Add integration tests for retrieval, product hydration, ranking, and price enrichment.

## Roadmap

- Replace TF-IDF similarity with sentence-transformer embeddings when catalog size and evaluation results justify the added complexity.
- Improve price forecasting with seasonal decomposition or Fourier features to better capture cyclical produce prices.
- Integrate `open_prices_client.py` into a scheduled ingestion workflow to gradually replace synthetic history with real contributed Australian price observations.
- Connect real purchase history from PostgreSQL to the optimizer's utility scoring.
- Run the backtest on real Australian price observations.
- Connect the specials-timing model to the live BUY/WAIT decision once it is validated on real data.
- Pass the user's candidate products from the chat route to the optimiser, with an end-to-end test.
- Fix or remove `app/services/decision_utility.py`, which shares the old inverted WAIT logic and is unused.
- Grow the agent evaluation set and report infrastructure errors (such as rate limits) separately from behaviour failures.
- Expand search relevance evaluation with a larger query set and human-judged relevance labels.
- Evaluate search performance under concurrent load and document operational limits.
- Improve handling of OpenSearch outages, timeouts, and recovery.
- Document the deployment architecture and service-to-service network configuration.

## Project Links

- **Live demo:** https://budgetbasket.tech
- **GitHub repository:** https://github.com/HieuTong/budgetbasket-ai
