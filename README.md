# BudgetBasket AI

A cost-of-living optimizer for Australian households: given your usual purchases and a budget, it builds a shopping basket that stays close to your habits while cutting cost — using classical ML, search and retrieval, retrieval-augmented generation, and an agentic tool-calling layer, not just a single LLM prompt.

**Live Demo:** https://budgetbasket.tech  
**GitHub:** https://github.com/HieuTong/budgetbasket-ai

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

Seasonal decomposition or a Fourier feature could help model such patterns. This remains a known limitation and a potential improvement.

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
- **CI:** GitHub Actions runs the configured import sanity check and Docker build.

See `DEPLOYMENT.md` for the backend deployment walkthrough.

The OpenSearch Azure VM is a separate search-infrastructure deployment. Do not assume that the public demo uses that instance unless the backend's configured endpoint confirms the connection.

For security, do not expose OpenSearch directly to the public internet. Restrict access to trusted services, protect credentials, and use appropriate network rules.

## Testing and Evaluation

The project uses automated checks and targeted evaluation to improve correctness and reliability.

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
- Add pytest coverage for the optimizer and RAG retriever.
- Expand search relevance evaluation with a larger query set and human-judged relevance labels.
- Evaluate search performance under concurrent load and document operational limits.
- Improve handling of OpenSearch outages, timeouts, and recovery.
- Document the deployment architecture and service-to-service network configuration.

## Project Links

- **Live demo:** https://budgetbasket.tech
- **GitHub repository:** https://github.com/HieuTong/budgetbasket-ai
