# OpenSearch product search prototype

This branch adds an opt-in OpenSearch retrieval backend for the existing catalog API.
PostgreSQL remains the source of truth for products and prices. OpenSearch returns
ranked product IDs; the existing catalog service loads canonical product records and
enriches them with price observations.

## Local setup

1. Start PostgreSQL and OpenSearch:

   ```bash
   docker compose up -d db opensearch
   ```

2. Install backend requirements and ensure the database schema and product data are
   present:

   ```bash
   cd backend
   pip install -r requirements.txt
   python -m seed.index_opensearch
   ```

   Run the indexer again to upsert changed product documents. For a full local rebuild,
   use `python -m seed.index_opensearch --recreate`; this deletes the configured index
   before rebuilding it.

3. Use OpenSearch for the API:

   ```bash
   # From the repository root; restart the backend after changing the environment.
   PRODUCT_SEARCH_BACKEND=opensearch docker compose up -d --build backend
   ```

   The default is `PRODUCT_SEARCH_BACKEND=legacy`, preserving the existing SQL
   substring search. When running the backend directly on the host, the default
   `OPENSEARCH_URL` is `http://localhost:9200`; inside Docker Compose it is
   `http://opensearch:9200`.

4. Query the unchanged endpoint:

   ```bash
   curl 'http://localhost:8000/products?search=greek%20yoghurt&limit=10'
   ```

## Current retrieval behavior

- BM25-style lexical ranking with field boosts for product name and brand.
- Phrase boost for product-name/brand matches.
- Automatic edit-distance fuzziness for lexical matches.
- Exact category filter.
- Stable product-ID ordering when no text query is supplied.
- Product and price details are enriched from PostgreSQL after retrieval.

## Operational boundaries

- This is a local prototype, not a production deployment configuration. The compose
  service disables the OpenSearch security plugin and must not be exposed publicly.
- Re-run the indexer after product changes. Automated change-data capture, deletes,
  aliases/zero-downtime reindexing, and production health checks are not implemented yet.
- The current index does not store prices. Price freshness and store/location selection
  remain PostgreSQL responsibilities.
- Nutrition fields are not currently validated numeric data; search relevance cannot
  guarantee dietary or nutrition constraints.
- Keep the search backend flag independent of `BASKET_PLANNER`. OpenSearch retrieval
  can be evaluated with the existing basket optimizer before SearchForge A* is enabled.

## Evaluation checklist

Use a fixed set of real queries with manually judged relevant products. Compare legacy
and OpenSearch results using Recall@10 and NDCG@10 where relevance labels are available,
plus zero-result rate, filter correctness, and p50/p95 latency. Do not report an
improvement until the benchmark has actually been run.
