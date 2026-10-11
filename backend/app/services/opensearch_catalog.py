"""OpenSearch-backed product retrieval; PostgreSQL remains authoritative."""

from __future__ import annotations

import os
from urllib.parse import urlparse


def create_client():
    """Create an OpenSearch client; callers own its lifecycle."""
    try:
        from opensearchpy import OpenSearch
    except ImportError as exc:
        raise RuntimeError(
            "OpenSearch is enabled but opensearch-py is missing; "
            "install backend requirements."
        ) from exc

    url = os.getenv("OPENSEARCH_URL", "http://localhost:9200")
    parsed = urlparse(url)

    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise RuntimeError("OPENSEARCH_URL must be an absolute http(s) URL.")

    use_ssl = parsed.scheme == "https"
    host = {
        "host": parsed.hostname,
        "port": parsed.port or (443 if use_ssl else 80),
    }

    username = os.getenv("OPENSEARCH_USERNAME") or parsed.username
    password = os.getenv("OPENSEARCH_PASSWORD") or parsed.password

    if username:
        if not password:
            raise RuntimeError(
                "OPENSEARCH_PASSWORD is required when OPENSEARCH_USERNAME is set."
            )
        host["http_auth"] = (username, password)

    access_client_id = os.getenv("CF_ACCESS_CLIENT_ID")
    access_client_secret = os.getenv("CF_ACCESS_CLIENT_SECRET")

    if bool(access_client_id) != bool(access_client_secret):
        raise RuntimeError(
            "CF_ACCESS_CLIENT_ID and CF_ACCESS_CLIENT_SECRET must be set together."
        )

    headers = {}
    if access_client_id and access_client_secret:
        headers = {
            "CF-Access-Client-Id": access_client_id,
            "CF-Access-Client-Secret": access_client_secret,
        }

    return OpenSearch(
        hosts=[host],
        use_ssl=use_ssl,
        verify_certs=use_ssl,
        http_auth=host.get("http_auth"),
        headers=headers,
        http_compress=True,
        timeout=10,
        max_retries=1,
        retry_on_timeout=True,
    )


def search_product_ids(
    *,
    search: str | None,
    category: str | None,
    limit: int,
    client=None,
) -> list[int]:
    """Return product IDs ranked by lexical relevance.

    An injected client is reused and remains owned by the caller.
    If no client is supplied, create and close a client for this call.
    """
    index = os.getenv("OPENSEARCH_PRODUCT_INDEX", "budgetbasket-products-v1")

    # Customer-facing grocery search should use the Australian catalog.
    # Historical Dunnhumby records remain in PostgreSQL for ML and analytics.
    customer_source = os.getenv(
        "OPENSEARCH_PRODUCT_SOURCE",
        "kaggle_australia_grocery_2022",
    )
    filters = [{"term": {"source": customer_source}}]

    if category and category.strip():
        filters.append({"term": {"category.keyword": category.strip()}})

    query_text = (search or "").strip()

    if query_text:
        # Avoid fuzzy expansion for short grocery terms.
        terms = query_text.split()
        allow_fuzzy = any(len(term) >= 5 for term in terms)

        product_match = {
            "multi_match": {
                "query": query_text,
                "type": "best_fields",
                "operator": "and",
                "fields": ["name^5", "brand^2"],
            }
        }
        if allow_fuzzy:
            product_match["multi_match"]["fuzziness"] = "AUTO"

        query = {
            "bool": {
                "should": [
                    {
                        "match_phrase": {
                            "name": {
                                "query": query_text,
                                "boost": 20,
                            }
                        }
                    },
                    product_match,
                    {
                        "multi_match": {
                            "query": query_text,
                            "type": "best_fields",
                            "fuzziness": "AUTO",
                            "operator": "and",
                            "fields": [
                                "sub_category^5",
                                "product_group^2",
                                "category^1",
                            ],
                        }
                    },
                    {
                        "term": {
                            "name.keyword": {
                                "value": query_text,
                                "boost": 30,
                            }
                        }
                    },
                    {
                        "match_phrase": {
                            "name": {
                                "query": query_text,
                                "boost": 12,
                            }
                        }
                    },
                    {
                        "match_phrase": {
                            "brand": {
                                "query": query_text,
                                "boost": 3,
                            }
                        }
                    },
                ],
                "minimum_should_match": 1,
                "filter": filters,
            }
        }
        sort = [
            {"_score": {"order": "desc"}},
            {"product_id": {"order": "asc"}},
        ]
    else:
        query = {
            "bool": {
                "filter": filters,
                "must": [{"match_all": {}}],
            }
        }
        sort = [{"product_id": {"order": "asc"}}]

    owns_client = client is None
    if owns_client:
        client = create_client()

    try:
        response = client.search(
            index=index,
            body={
                "size": limit,
                "track_total_hits": False,
                "query": query,
                "sort": sort,
            },
        )
    finally:
        if owns_client:
            client.close()

    product_ids = []
    for hit in response.get("hits", {}).get("hits", []):
        product_id = hit.get("_source", {}).get("product_id")
        if product_id is not None:
            product_ids.append(int(product_id))

    return product_ids
