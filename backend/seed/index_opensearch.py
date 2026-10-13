"""Index PostgreSQL products into OpenSearch.

Run from backend/: python -m seed.index_opensearch
Use --recreate to delete and rebuild the configured index (local/dev only).
"""
from __future__ import annotations

import argparse
import os

from opensearchpy import OpenSearch, helpers

from app.db.models import Product
from app.db.session import SessionLocal

from app.core.config import BACKEND_DIR
from dotenv import load_dotenv

load_dotenv(BACKEND_DIR / ".env")


INDEX = os.getenv("OPENSEARCH_PRODUCT_INDEX", "budgetbasket-products-v1")
URL = os.getenv("OPENSEARCH_URL", "http://localhost:9200")


def make_client() -> OpenSearch:
    from urllib.parse import urlparse

    parsed = urlparse(URL)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise ValueError("OPENSEARCH_URL must be an absolute http(s) URL.")

    secure = parsed.scheme == "https"
    username = os.getenv("OPENSEARCH_USERNAME")
    password = os.getenv("OPENSEARCH_PASSWORD")
    access_client_id = os.getenv("CF_ACCESS_CLIENT_ID")
    access_client_secret = os.getenv("CF_ACCESS_CLIENT_SECRET")

    if bool(username) != bool(password):
        raise ValueError(
            "OPENSEARCH_USERNAME and OPENSEARCH_PASSWORD must be set together."
        )

    if bool(access_client_id) != bool(access_client_secret):
        raise ValueError(
            "CF_ACCESS_CLIENT_ID and CF_ACCESS_CLIENT_SECRET must be set together."
        )

    headers = {}
    if access_client_id and access_client_secret:
        headers = {
            "CF-Access-Client-Id": access_client_id,
            "CF-Access-Client-Secret": access_client_secret,
        }

    kwargs = {}
    if username and password:
        kwargs["http_auth"] = (username, password)

    return OpenSearch(
        hosts=[{
            "host": parsed.hostname,
            "port": parsed.port or (443 if secure else 80),
        }],
        use_ssl=secure,
        verify_certs=secure,
        headers=headers,
        timeout=10,
        max_retries=2,
        retry_on_timeout=True,
        **kwargs,
    )

def ensure_index(client: OpenSearch, *, recreate: bool) -> None:
    if recreate and client.indices.exists(index=INDEX):
        client.indices.delete(index=INDEX)

    if client.indices.exists(index=INDEX):
        return

    client.indices.create(
        index=INDEX,
        body={
            "settings": {
                "number_of_shards": 1,
                "number_of_replicas": 0,
                "analysis": {
                    "normalizer": {
                        "lowercase_normalizer": {
                            "type": "custom",
                            "filter": ["lowercase", "asciifolding"],
                        }
                    }
                },
            },
            "mappings": {
                "dynamic": "strict",
                "properties": {
                    "product_id": {"type": "integer"},
                    "name": {
                        "type": "text",
                        "fields": {
                            "keyword": {
                                "type": "keyword",
                                "normalizer": "lowercase_normalizer",
                            }
                        },
                    },
                    "brand": {
                        "type": "text",
                        "fields": {
                            "keyword": {
                                "type": "keyword",
                                "normalizer": "lowercase_normalizer",
                            }
                        },
                    },
                    "category": {
                        "type": "text",
                        "fields": {
                            "keyword": {
                                "type": "keyword",
                                "normalizer": "lowercase_normalizer",
                            }
                        },
                    },
                    "sub_category": {"type": "text"},
                    "product_group": {"type": "text"},
                    "package_size": {"type": "keyword"},
                    "barcode": {"type": "keyword"},
                    "source": {"type": "keyword"},
                    "source_product_id": {"type": "keyword"},
                },
            },
        },
    )

def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--recreate",
        action="store_true",
        help="Delete and rebuild the index; use only for local/dev indexing.",
    )
    args = parser.parse_args()

    client = make_client()
    db = SessionLocal()
    try:
        ensure_index(client, recreate=args.recreate)

        def actions():
            query = db.query(Product).order_by(Product.id.asc()).yield_per(500)
            for product in query:
                yield {
                    "_op_type": "index",
                    "_index": INDEX,
                    "_id": str(product.id),
                    "_source": {
                        "product_id": product.id,
                        "name": product.name or "",
                        "brand": product.brand or "",
                        "category": product.category or "",
                        "sub_category": product.sub_category or "",
                        "product_group": product.product_group or "",
                        "package_size": product.package_size or "",
                        "barcode": product.barcode or "",
                        "source": product.source or "",
                        "source_product_id": product.source_product_id or "",
                    },
                }

        success, errors = helpers.bulk(
            client,
            actions(),
            chunk_size=500,
            request_timeout=60,
            raise_on_error=False,
        )
        client.indices.refresh(index=INDEX)
        print(f"Indexed {success} products into {INDEX}.")
        if errors:
            raise RuntimeError(f"{len(errors)} product documents failed to index.")
    finally:
        db.close()
        client.close()


if __name__ == "__main__":
    main()
