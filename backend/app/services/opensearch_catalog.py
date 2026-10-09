"""OpenSearch-backed product retrieval; PostgreSQL remains authoritative."""
from __future__ import annotations

import os
from urllib.parse import urlparse


def _client():
    try:
        from opensearchpy import OpenSearch
    except ImportError as exc:
        raise RuntimeError(
            "OpenSearch is enabled but opensearch-py is missing; install backend requirements."
        ) from exc

    url = os.getenv("OPENSEARCH_URL", "http://localhost:9200")
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise RuntimeError("OPENSEARCH_URL must be an absolute http(s) URL.")
    use_ssl = parsed.scheme == "https"
    host = {"host": parsed.hostname, "port": parsed.port or (443 if use_ssl else 80)}
    if parsed.username:
        host["http_auth"] = (parsed.username, parsed.password or "")
    return OpenSearch(
        hosts=[host], use_ssl=use_ssl, verify_certs=use_ssl,
        http_compress=True, timeout=3, max_retries=1, retry_on_timeout=True,
    )


def search_product_ids(*, search: str | None, category: str | None, limit: int) -> list[int]:
    """Return product IDs ranked by lexical relevance."""
    index = os.getenv("OPENSEARCH_PRODUCT_INDEX", "budgetbasket-products-v1")
    filters = []
    if category and category.strip():
        filters.append({"term": {"category.keyword": category.strip()}})
    query_text = (search or "").strip()
    if query_text:
        query = {
            "bool": {
                "must": [{"multi_match": {
                    "query": query_text, "type": "best_fields", "fuzziness": "AUTO",
                    "fields": ["name^5", "brand^3", "sub_category^2", "product_group", "category"],
                }}],
                "should": [{"multi_match": {
                    "query": query_text, "type": "phrase", "fields": ["name^8", "brand^4"], "boost": 2,
                }}],
                "filter": filters,
            }
        }
        sort = [{"_score": {"order": "desc"}}, {"product_id": {"order": "asc"}}]
    else:
        query = {"bool": {"filter": filters, "must": [{"match_all": {}}]}}
        sort = [{"product_id": {"order": "asc"}}]

    client = _client()
    try:
        response = client.search(index=index, body={
            "size": limit, "track_total_hits": False, "query": query, "sort": sort,
        })
    finally:
        client.close()

    ids = []
    for hit in response.get("hits", {}).get("hits", []):
        product_id = hit.get("_source", {}).get("product_id")
        if product_id is not None:
            ids.append(int(product_id))
    return ids
