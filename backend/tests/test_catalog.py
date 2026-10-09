import pytest
from types import SimpleNamespace
from unittest.mock import Mock
from opensearchpy.exceptions import ConnectionError as OpenSearchConnectionError

from app.services import catalog
from opensearchpy.exceptions import (
    ConnectionError as OpenSearchConnectionError,
    TransportError,
)


def test_list_catalog_falls_back_to_postgres_on_opensearch_connection_error(
    monkeypatch,
):
    product = SimpleNamespace(
        id=17,
        name="Greek yoghurt",
        brand="Example",
        category="Dairy",
        sub_category="Yoghurt",
        package_size="500 g",
        unit="g",
        unit_price=4.50,
    )

    postgres_search = Mock(return_value=[product])
    latest_prices = Mock(return_value={})
    opensearch_search = Mock(
        side_effect=OpenSearchConnectionError(
            "N/A",
            "OpenSearch unavailable",
            None,
        )
)

    monkeypatch.setenv("PRODUCT_SEARCH_BACKEND", "opensearch")
    monkeypatch.setattr(catalog, "list_products", postgres_search)
    monkeypatch.setattr(catalog, "get_latest_prices_for_products", latest_prices)
    monkeypatch.setattr(
        "app.services.opensearch_catalog.search_product_ids",
        opensearch_search,
    )

    db = Mock()
    result = catalog.list_catalog(
        db=db,
        category="Dairy",
        search="Greek yoghurt",
        limit=10,
    )

    opensearch_search.assert_called_once_with(
        search="Greek yoghurt",
        category="Dairy",
        limit=10,
    )
    postgres_search.assert_called_once_with(
        db,
        category="Dairy",
        search="Greek yoghurt",
        limit=10,
    )
    assert result[0]["product_id"] == 17
    assert result[0]["name"] == "Greek yoghurt"
    assert result[0]["price"] == 4.50


def test_list_catalog_reraises_non_transient_opensearch_error(monkeypatch):

    opensearch_search = Mock(
        side_effect=TransportError(
            400,
            "Bad Request",
            {"error": "invalid query"},
        )
    )
    postgres_search = Mock()

    monkeypatch.setenv("PRODUCT_SEARCH_BACKEND", "opensearch")
    monkeypatch.setattr(catalog, "list_products", postgres_search)
    monkeypatch.setattr(
        "app.services.opensearch_catalog.search_product_ids",
        opensearch_search,
    )

    with pytest.raises(TransportError):
        catalog.list_catalog(
            db=Mock(),
            category="Dairy",
            search="Greek yoghurt",
            limit=10,
        )

    postgres_search.assert_not_called()
