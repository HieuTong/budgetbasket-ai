from fastapi.testclient import TestClient

from app.api.routes import catalog as catalog_route
from app.db.session import get_db
from app.main import app
from app.services import opensearch_catalog


class FakeOpenSearchClient:
    def __init__(self):
        self.closed = False

    def close(self):
        self.closed = True


def test_opensearch_client_is_shared_with_route_and_closed_on_shutdown(
    monkeypatch,
):
    monkeypatch.setenv("PRODUCT_SEARCH_BACKEND", "opensearch")

    client = FakeOpenSearchClient()
    created_clients = []

    def fake_create_client():
        created_clients.append(client)
        return client

    monkeypatch.setattr(
        "app.main.create_client",
        fake_create_client,
    )
    received = {}

    def fake_list_catalog(
        db,
        category=None,
        search=None,
        limit=None,
        opensearch_client=None,
    ):
        received["client"] = opensearch_client
        return []

    monkeypatch.setattr(
        catalog_route,
        "list_catalog",
        fake_list_catalog,
    )

    def override_get_db():
        yield object()

    monkeypatch.setitem(
        app.dependency_overrides,
        get_db,
        override_get_db,
    )

    with TestClient(app) as test_client:
        response = test_client.get("/api/catalog/products")

        assert response.status_code == 200
        assert response.json() == {"items": []}
        assert created_clients == [client]
        assert received["client"] is client
        assert client.closed is False

    assert client.closed is True


def test_legacy_lifespan_does_not_create_opensearch_client(monkeypatch):
    monkeypatch.setenv("PRODUCT_SEARCH_BACKEND", "legacy")

    def unexpected_client_creation():
        raise AssertionError(
            "Legacy mode must not create an OpenSearch client."
        )

    monkeypatch.setattr(
        opensearch_catalog,
        "create_client",
        unexpected_client_creation,
    )

    with TestClient(app):
        assert app.state.opensearch_client is None
