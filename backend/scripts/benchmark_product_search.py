from __future__ import annotations

import statistics
import time

from app.db.session import SessionLocal
from app.db.repositories.products import list_products
from app.db.repositories.products import get_products_by_ids_ordered
from app.services.opensearch_catalog import search_product_ids


QUERIES = ["oat milk", "milk", "organic eggs", "chiken", "almond"]
LIMIT = 5
RUNS = 3


def timed_search(fn):
    durations = []
    result = []

    for _ in range(RUNS):
        start = time.perf_counter()
        result = fn()
        durations.append((time.perf_counter() - start) * 1000)

    return result, statistics.median(durations)


def main():
    db = SessionLocal()

    try:
        for query in QUERIES:
            print(f"\n{'=' * 65}\nQuery: {query!r}")

            pg_products, pg_ms = timed_search(
                lambda: list_products(db, search=query, limit=LIMIT)
            )

            def opensearch_lookup():
                ids = search_product_ids(
                    search=query, category=None, limit=LIMIT
                )
                return get_products_by_ids_ordered(db, ids)

            os_products, os_ms = timed_search(opensearch_lookup)

            print(f"\nPostgreSQL median: {pg_ms:.2f} ms")
            for rank, product in enumerate(pg_products, start=1):
                print(f"  {rank}. [{product.id}] {product.name} | {product.brand}")

            print(f"\nOpenSearch + PostgreSQL fetch median: {os_ms:.2f} ms")
            for rank, product in enumerate(os_products, start=1):
                print(f"  {rank}. [{product.id}] {product.name} | {product.brand}")

    finally:
        db.close()


if __name__ == "__main__":
    main()
