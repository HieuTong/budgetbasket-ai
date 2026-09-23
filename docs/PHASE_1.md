# Phase 1 — Real Data Foundation

## Goal

Turn BudgetBasket from a demo that can calculate a basket into a backend system with a persistent, provenance-aware grocery catalog and canonical price observations.

Phase 1 intentionally does **not** build fraud detection, Stripe payments, the LLM agent, or the final DecisionOS engine. Those layers consume this foundation later.

## Phase 1A scope

- PostgreSQL is the system of record.
- Alembic is the only schema creation/evolution mechanism.
- The existing 55-item Australian grocery snapshot remains the small development dataset.
- Synthetic history is explicitly labelled `synthetic_seed` and `is_estimated=true`.
- Canonical price data lives in `price_observations`.
- `price_history` remains temporarily populated for compatibility with existing forecasting code.
- Store is optional because the Phase 1A snapshot has no retailer dimension.
- Repository code owns database access.
- Services own application-level composition.
- FastAPI routes expose the catalog without coupling directly to SQLAlchemy queries.

## Migration chain

```text
20260922_00_initial_schema
        ↓
20260922_01_canonical_price_observations
        ↓
20260922_02_optional_store
```

A fresh `budgetbasket` database must be buildable with:

```bash
cd backend
alembic upgrade head
```

Do not use `Base.metadata.create_all()` for application setup.

## Local configuration

Create a local file that is ignored by Git:

```bash
cd backend
cp .env.example .env
```

Set `DATABASE_URL` to the local PostgreSQL database. `app.core.config` resolves this file relative to the backend source tree, so Alembic, tests, seed jobs, and Uvicorn use the same configuration regardless of the current working directory.

## Seed pipeline

After migrations:

```bash
python -m seed.load_seed_data
```

The loader is idempotent for its synthetic price observations using a deterministic source record ID.

Expected development dataset:

- 55 products
- 91 daily observations per product
- 5,005 canonical price observations
- source = `synthetic_seed`
- `is_estimated = true`

The values are suitable for local development and demonstrations, but must not be described as live Australian retail prices.

## Phase 1 API

### Catalog

```http
GET /api/catalog/products
GET /api/catalog/products?category=dairy
GET /api/catalog/products/{product_id}/prices
```

The catalog service reads the latest canonical observation rather than treating the product's static `unit_price` as the authoritative current price.

The latest-price lookup is batched to avoid an N+1 query pattern.

## Verification checklist

1. PostgreSQL accepts the `postgres` connection.
2. `alembic upgrade head` succeeds on an empty database.
3. `alembic current` reports `20260922_02`.
4. `\\dt` shows the expected application tables plus `alembic_version`.
5. Seed loader inserts 55 products and 5,005 price observations.
6. Re-running the seed loader does not duplicate observations.
7. `GET /health` returns HTTP 200.
8. `GET /api/catalog/products` returns the seeded catalog.
9. `GET /api/catalog/products?category=dairy` returns only dairy products.
10. `GET /api/catalog/products/{id}/prices` returns chronological price observations.
11. An unknown product returns HTTP 404.

## Why this is senior-engineering work

The important design decision is not the number of tables. It is separating:

```text
data acquisition
      ↓
canonical observation model
      ↓
repository
      ↓
service
      ↓
API
      ↓
decision/ML layer
```

This lets a later AusCost/Open Prices adapter replace the seed source without forcing the optimizer or API to understand the external dataset's schema.

## Phase 1B — next

Replace or supplement the synthetic snapshot with real public price observations through an ingestion adapter. Real observations must retain source and provenance metadata and should populate `price_observations` without changing the decision layer.
