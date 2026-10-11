from __future__ import annotations

import argparse
import json
import logging
import math
import os
import statistics
import time
from collections import Counter, defaultdict
from datetime import date, datetime
from pathlib import Path

from app.db.session import SessionLocal
from app.services.catalog import list_catalog
from app.services.opensearch_catalog import create_client


QUERIES = [
    "almond milk",
    "soy milk",
    "chicken",
    "chiken",
    "oat milk",
    "coconut milk",
]

BACKENDS = ("legacy", "opensearch")
DEFAULT_LIMIT = 5
DEFAULT_WARMUPS = 3
DEFAULT_ITERATIONS = 20

logger = logging.getLogger("app.services.catalog")


class FallbackCapture(logging.Handler):
    """Count catalog requests that fall back from OpenSearch to PostgreSQL."""

    def __init__(self) -> None:
        super().__init__(level=logging.WARNING)
        self.count = 0

    def emit(self, record: logging.LogRecord) -> None:
        message = record.getMessage().lower()
        if "falling back to postgresql" in message:
            self.count += 1


def percentile95(values: list[float]) -> float | None:
    """Calculate nearest-rank p95."""
    if not values:
        return None
    ordered = sorted(values)
    return ordered[math.ceil(0.95 * len(ordered)) - 1]


def summarize(values: list[float]) -> dict:
    if not values:
        return {
            "successful_runs": 0,
            "median_ms": None,
            "p95_ms": None,
            "min_ms": None,
            "max_ms": None,
        }

    return {
        "successful_runs": len(values),
        "median_ms": round(statistics.median(values), 2),
        "p95_ms": round(percentile95(values), 2),
        "min_ms": round(min(values), 2),
        "max_ms": round(max(values), 2),
    }


def is_relevant(query: str, product: dict) -> bool:
    """Rule-based relevance heuristic, not human-judged ground truth."""
    name = str(product.get("name") or "").lower()
    category = str(product.get("category") or "").lower()
    sub_category = str(product.get("sub_category") or "").lower()

    # Exclude confectionery based on taxonomy, not flavour words.
    if any(
        term in f"{category} {sub_category}"
        for term in ("confectionery", "candy", "lolly")
    ):
        return False

    if query in {"chicken", "chiken"}:
        return sub_category == "poultry"

    if query == "almond milk":
        return "almond" in name and sub_category == "milk"

    if query == "soy milk":
        return (
            any(term in name for term in ("soy", "soya"))
            and sub_category == "milk"
        )

    if query == "oat milk":
        return "oat" in name and "milk" in name and sub_category == "milk"

    if query == "coconut milk":
        return "coconut" in name and "milk" in name and sub_category == "milk"

    return False

def precision_at_k(query: str, products: list[dict], k: int) -> float:
    """Precision@k uses k as denominator even when fewer than k items are returned."""
    top_k = products[:k]
    return sum(is_relevant(query, item) for item in top_k) / k


def json_safe(value):
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    return str(value)


def run_once(db, backend: str, query: str, limit: int, client):
    os.environ["PRODUCT_SEARCH_BACKEND"] = backend
    return list_catalog(
        db,
        search=query,
        limit=limit,
        opensearch_client=client if backend == "opensearch" else None,
    )


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Compare the production PostgreSQL and OpenSearch catalog paths."
    )
    parser.add_argument("--iterations", type=int, default=DEFAULT_ITERATIONS)
    parser.add_argument("--warmups", type=int, default=DEFAULT_WARMUPS)
    parser.add_argument("--limit", type=int, default=DEFAULT_LIMIT)
    parser.add_argument(
        "--json-out",
        type=Path,
        default=None,
        help="Optional path for a machine-readable JSON report.",
    )
    args = parser.parse_args()

    if args.iterations < 1 or args.warmups < 0 or args.limit < 1:
        parser.error("--iterations and --limit must be positive; --warmups cannot be negative.")

    if not os.getenv("OPENSEARCH_URL"):
        parser.error(
            "OPENSEARCH_URL is not set. Configure your hosted OpenSearch endpoint "
            "in the environment before running this benchmark."
        )

    db = SessionLocal()
    client = None
    fallback_capture = FallbackCapture()
    logger.addHandler(fallback_capture)

    timings = defaultdict(list)
    errors = Counter()
    empty_results = Counter()
    fallback_events = Counter()
    result_counts = defaultdict(list)
    precision_scores = defaultdict(list)
    final_results = {}

    try:
        # Create one client for the benchmark; do not include client creation in latency.
        client = create_client()

        print("Product search benchmark")
        print(f"Queries: {len(QUERIES)}")
        print(f"Warm-ups per backend/query: {args.warmups}")
        print(f"Measured runs per backend/query: {args.iterations}")
        print(f"Result limit: {args.limit}")
        print("Latency includes catalog retrieval, reranking, hydration, and price lookup.")
        print("OpenSearch client creation is excluded from measured latency.")
        print("Relevance is heuristic and should be manually validated before publication.")

        # Warm up both paths for every query; do not include these runs in metrics.
        for query in QUERIES:
            for backend in BACKENDS:
                for _ in range(args.warmups):
                    try:
                        run_once(db, backend, query, args.limit, client)
                    except Exception as exc:
                        print(
                            f"WARNING: warm-up failed: backend={backend}, "
                            f"query={query!r}, error={type(exc).__name__}: {exc}"
                        )

        # Alternate backend order by iteration to reduce consistent ordering bias.
        for iteration in range(args.iterations):
            backend_order = BACKENDS if iteration % 2 == 0 else BACKENDS[::-1]

            for query in QUERIES:
                for backend in backend_order:
                    fallback_before = fallback_capture.count
                    started = time.perf_counter()

                    try:
                        products = run_once(
                            db, backend, query, args.limit, client
                        )
                        elapsed_ms = (time.perf_counter() - started) * 1000
                        timings[(backend, query)].append(elapsed_ms)
                        result_counts[(backend, query)].append(len(products))

                        if not products:
                            empty_results[(backend, query)] += 1

                        final_results[(backend, query)] = products
                        precision_scores[(backend, query)].append(
                            precision_at_k(query, products, args.limit)
                        )
                    except Exception as exc:
                        errors[(backend, query)] += 1
                        print(
                            f"ERROR: backend={backend}, query={query!r}, "
                            f"iteration={iteration + 1}, "
                            f"{type(exc).__name__}: {exc}"
                        )

                    finally:
                        fallback_delta = fallback_capture.count - fallback_before
                        if fallback_delta:
                            fallback_events[(backend, query)] += fallback_delta

        report = {
            "configuration": {
                "queries": QUERIES,
                "backends": list(BACKENDS),
                "warmups_per_backend_query": args.warmups,
                "measured_iterations_per_backend_query": args.iterations,
                "limit": args.limit,
                "latency_scope": (
                    "Full list_catalog path; OpenSearch client creation excluded"
                ),
                "p95_method": "Nearest-rank percentile",
                "relevance_method": (
                    "Mean Precision@k across successful measured runs; "
                    "rule-based heuristic, not human-judged ground truth"
                ),
            },
            "results": [],
        }

        print("\n" + "=" * 100)
        print("SUMMARY")
        print("=" * 100)

        for query in QUERIES:
            for backend in BACKENDS:
                key = (backend, query)
                latency = summarize(timings[key])
                successful = latency["successful_runs"]
                requested = args.iterations
                fallback_count = fallback_events[key]
                error_count = errors[key]
                empty_count = empty_results[key]
                products = final_results.get(key, [])
                relevance_runs = precision_scores[key]
                mean_relevance = (
                    statistics.mean(relevance_runs) if relevance_runs else None
                )

                item = {
                    "backend": backend,
                    "query": query,
                    **latency,
                    "requested_runs": requested,
                    "errors": error_count,
                    "empty_results": empty_count,
                    "fallback_events": fallback_count,
                    "mean_result_count": (
                        round(statistics.mean(result_counts[key]), 2)
                        if result_counts[key]
                        else None
                    ),
                    "successful_relevance_runs": len(relevance_runs),
                    "mean_precision_at_k_heuristic": (
                        round(mean_relevance, 3)
                        if mean_relevance is not None
                        else None
                    ),
                    "last_successful_results": [
                        {
                            "product_id": product.get("product_id"),
                            "name": product.get("name"),
                            "category": product.get("category"),
                            "sub_category": product.get("sub_category"),
                        }
                        for product in products
                    ],
                }
                report["results"].append(item)

                print(
                    f"{query!r:18} {backend:10} "
                    f"median={str(latency['median_ms']):>8} ms  "
                    f"p95={str(latency['p95_ms']):>8} ms  "
                    f"success={successful}/{requested}  "
                    f"errors={error_count}  empty={empty_count}  "
                    f"fallbacks={fallback_count}  "
                    f"mean_count={item['mean_result_count']}  "
                    f"mean_P@{args.limit}="
                    f"{item['mean_precision_at_k_heuristic']}"
                )

                print("  Last successful result set:")
                if products:
                    for rank, product in enumerate(products[:args.limit], start=1):
                        relevant = is_relevant(query, product)
                        print(
                            f"    {rank}. {'[relevant]' if relevant else '[not relevant]'} "
                            f"{product.get('name')} | "
                            f"{product.get('category')} | "
                            f"{product.get('sub_category')}"
                        )
                else:
                    print("    No successful results available.")

        print("\nInterpretation notes:")
        print("- A fallback means the requested OpenSearch path used PostgreSQL instead.")
        print("- Treat OpenSearch latency as contaminated if fallback_events > 0.")
        print("- Empty results are counted separately from errors.")
        print("- Heuristic Precision@5 is a preliminary indicator, not an expert relevance assessment.")
        print("- These measurements describe this environment and run; they do not prove general performance.")

        if args.json_out:
            args.json_out.parent.mkdir(parents=True, exist_ok=True)
            args.json_out.write_text(
                json.dumps(report, indent=2, default=json_safe) + "\n",
                encoding="utf-8",
            )
            print(f"\nJSON report written to: {args.json_out}")

        total_errors = sum(errors.values())
        total_fallbacks = sum(fallback_events.values())
        return 1 if total_errors or total_fallbacks else 0

    finally:
        logger.removeHandler(fallback_capture)
        if client is not None:
            client.close()
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
