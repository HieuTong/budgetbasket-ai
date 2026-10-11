from __future__ import annotations

import statistics
import time

from app.db.repositories.products import (
    get_products_by_ids_ordered,
    list_products,
)
from app.db.session import SessionLocal
from app.services.opensearch_catalog import create_client, search_product_ids


QUERIES = ["oat milk", "milk", "organic eggs", "chiken", "almond"]
LIMIT = 5
WARMUP_RUNS = 2
MEASURED_RUNS = 10


def measure(fn):
    for _ in range(WARMUP_RUNS):
        fn()

    durations = []
    result = None

    for _ in range(MEASURED_RUNS):
        start = time.perf_counter()
        result = fn()
        durations.append((time.perf_counter() - start) * 1000)

    return result, {
        "median": statistics.median(durations),
        "min": min(durations),
        "max": max(durations),
    }


def show_timing(label, timing):
    print(
        f"{label}: median={timing['median']:.2f} ms, "
        f"min={timing['min']:.2f} ms, max={timing['max']:.2f} ms"
    )


def show_products(products):
    if not products:
        print("  No products returned.")
        return

    for rank, product in enumerate(products, start=1):
        print(f"  {rank}. [{product.id}] {product.name} | {product.brand}")


def main():
    db = SessionLocal()
    client = None

    try:
        client = create_client()

        for query in QUERIES:
            print(f"\n{'=' * 65}\nQuery: {query!r}")

            pg_products, pg_timing = measure(
                lambda: list_products(db, search=query, limit=LIMIT)
            )

            ids, search_timing = measure(
                lambda: search_product_ids(
                    search=query,
                    category=None,
                    limit=LIMIT,
                    client=client,
                )
            )

            products, hydration_timing = measure(
                lambda: get_products_by_ids_ordered(db, ids)
            )

            show_timing("PostgreSQL search", pg_timing)
            show_products(pg_products)

            show_timing("OpenSearch query only", search_timing)
            show_timing("PostgreSQL hydration only", hydration_timing)
            print(
                "OpenSearch + PostgreSQL hydration (approximate median sum): "
                f"{search_timing['median'] + hydration_timing['median']:.2f} ms"
            )
            show_products(products)

    finally:
        if client is not None:
            client.close()
        db.close()


if __name__ == "__main__":
    main()
