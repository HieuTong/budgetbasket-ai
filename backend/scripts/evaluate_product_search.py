
from __future__ import annotations

import math

from app.services.opensearch_catalog import create_client, search_product_ids


LIMIT = 5

# Provisional human judgements based on the products inspected so far.
# Grades: 0 = irrelevant, 1 = partially relevant,
#         2 = relevant, 3 = highly relevant.
# These are evaluation labels, NOT ranking rules.
JUDGEMENTS = {
    "milk": {
        12294: 3, 12794: 3, 14871: 3, 15720: 3, 16363: 3,
        50623: 0, 54377: 0, 58753: 0, 75282: 0, 87951: 0,
    },
    "oat milk": {
        14577: 1,  # Chocolate product containing oat milk; not oat milk itself.
        14364: 0, 12793: 0, 13941: 0, 17315: 0,
        53692: 0, 58256: 0, 58984: 0,
    },
    "organic eggs": {
        17492: 3, 14424: 3,
    },
    "chiken": {
        # No positive judgements yet. Collect actual chicken-meat results
        # before evaluating this query.
    },
    "almond": {
        12468: 3, 13894: 3, 15276: 3, 15992: 3, 16087: 3,
        12449: 2, 12470: 2, 12555: 2, 12558: 2,
    },
}


def dcg(grades: list[int]) -> float:
    return sum(
        (2**grade - 1) / math.log2(rank + 1)
        for rank, grade in enumerate(grades, start=1)
    )


def evaluate(query: str, result_ids: list[int]) -> None:
    judgements = JUDGEMENTS[query]
    unjudged = [pid for pid in result_ids if pid not in judgements]

    print(f"\nQuery: {query!r}")
    print(f"Top {LIMIT} IDs: {result_ids}")

    if unjudged:
        print(f"Evaluation pending: label these result IDs first: {unjudged}")
        return

    grades = [judgements[pid] for pid in result_ids]
    ideal_grades = sorted(judgements.values(), reverse=True)[:LIMIT]

    ideal_dcg = dcg(ideal_grades)
    if ideal_dcg == 0:
        print("Not evaluated: no positive relevance judgements.")
        return

    ndcg = dcg(grades) / ideal_dcg

    # MRR considers grades >= 2 relevant; partial matches alone don't count.
    relevant_ranks = [
        rank for rank, grade in enumerate(grades, start=1)
        if grade >= 2
    ]
    mrr = 1 / relevant_ranks[0] if relevant_ranks else 0.0

    print(f"NDCG@{LIMIT}: {ndcg:.3f}")
    print(f"MRR@{LIMIT}:  {mrr:.3f}")


def main() -> None:
    client = create_client()
    try:
        for query in JUDGEMENTS:
            ids = search_product_ids(
                search=query,
                category=None,
                limit=LIMIT,
                client=client,
            )
            evaluate(query, ids)
    finally:
        client.close()


if __name__ == "__main__":
    main()
