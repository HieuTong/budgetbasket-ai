import asyncio

from fastapi import FastAPI

from app.services import opensearch_catalog


class FakeClient:
    def __init__(self, response):
        self.response = response
        self.calls = []
        self.closed = False

    def search(self, **kwargs):
        self.calls.append(kwargs)
        return self.response

    def close(self):
        self.closed = True


def test_search_product_ids_returns_ranked_ids_and_boosts_name():
    client = FakeClient(
        {
            "hits": {
                "hits": [
                    {"_source": {"product_id": 17}},
                    {"_source": {"product_id": 4}},
                ]
            }
        }
    )

    result = opensearch_catalog.search_product_ids(
        search="Greek yoghurt",
        category="Dairy",
        limit=10,
        client=client,
    )

    assert result == [17, 4]

    request = client.calls[0]
    assert request["index"] == "budgetbasket-products-v1"

    query = request["body"]["query"]["bool"]
    assert query["filter"] == [
        {"term": {"source": "kaggle_australia_grocery_2022"}},
        {"term": {"category.keyword": "Dairy"}},
    ]
    assert query["minimum_should_match"] == 1

    should = query["should"]
    name_phrase = should[0]["match_phrase"]["name"]
    assert name_phrase["query"] == "Greek yoghurt"
    assert name_phrase["boost"] == 20

    product_match = should[1]["multi_match"]
    assert product_match["fields"] == ["name^5", "brand^2"]
    assert product_match["fuzziness"] == "AUTO"
    assert product_match["operator"] == "and"

    taxonomy_match = should[2]["multi_match"]
    assert taxonomy_match["fields"] == [
        "sub_category^5",
        "product_group^2",
        "category^1",
    ]
    assert taxonomy_match["fuzziness"] == "AUTO"

    exact_name = should[3]["term"]["name.keyword"]
    assert exact_name == {"value": "Greek yoghurt", "boost": 30}
    assert should[4]["match_phrase"]["name"]["boost"] == 12
    assert should[5]["match_phrase"]["brand"]["boost"] == 3

    assert request["body"]["sort"][0] == {"_score": {"order": "desc"}}

    # The caller owns an injected client.
    assert client.closed is False


def test_search_product_ids_empty_query_uses_stable_id_order():
    client = FakeClient(
        {
            "hits": {
                "hits": [
                    {"_source": {"product_id": 2}},
                    {"_source": {"product_id": 9}},
                ]
            }
        }
    )

    result = opensearch_catalog.search_product_ids(
        search="  ",
        category=None,
        limit=20,
        client=client,
    )

    assert result == [2, 9]
    assert client.calls[0]["body"]["sort"] == [
        {"product_id": {"order": "asc"}}
    ]
    assert client.closed is False


def test_search_product_ids_filters_to_customer_catalog_without_category():
    client = FakeClient({"hits": {"hits": []}})

    opensearch_catalog.search_product_ids(
        search="milk",
        category=None,
        limit=5,
        client=client,
    )

    query = client.calls[0]["body"]["query"]["bool"]
    assert query["filter"] == [
        {"term": {"source": "kaggle_australia_grocery_2022"}}
    ]


def test_search_product_ids_ignores_hits_without_product_id():
    client = FakeClient(
        {
            "hits": {
                "hits": [
                    {"_source": {}},
                    {"_source": {"product_id": 3}},
                ]
            }
        }
    )

    result = opensearch_catalog.search_product_ids(
        search="milk",
        category=None,
        limit=5,
        client=client,
    )

    assert result == [3]
    assert client.closed is False


def test_search_product_ids_reuses_injected_client():
    client = FakeClient(
        {
            "hits": {
                "hits": [{"_source": {"product_id": 12}}],
            }
        }
    )

    first_result = opensearch_catalog.search_product_ids(
        search="milk",
        category=None,
        limit=5,
        client=client,
    )
    second_result = opensearch_catalog.search_product_ids(
        search="bread",
        category=None,
        limit=5,
        client=client,
    )

    assert first_result == [12]
    assert second_result == [12]
    assert len(client.calls) == 2
    assert client.closed is False


def test_search_product_ids_creates_and_closes_standalone_client(monkeypatch):
    client = FakeClient(
        {
            "hits": {
                "hits": [{"_source": {"product_id": 8}}],
            }
        }
    )
    created_clients = []

    def fake_create_client():
        created_clients.append(client)
        return client

    monkeypatch.setattr(
        opensearch_catalog,
        "create_client",
        fake_create_client,
    )

    result = opensearch_catalog.search_product_ids(
        search="eggs",
        category=None,
        limit=5,
    )

    assert result == [8]
    assert created_clients == [client]
    assert client.closed is True


def test_owned_client_is_closed_when_search_fails(monkeypatch):
    class FailingClient(FakeClient):
        def search(self, **kwargs):
            raise RuntimeError("search failed")

    client = FailingClient({"hits": {"hits": []}})
    monkeypatch.setattr(
        opensearch_catalog,
        "create_client",
        lambda: client,
    )

    try:
        opensearch_catalog.search_product_ids(
            search="milk",
            category=None,
            limit=5,
        )
    except RuntimeError as exc:
        assert str(exc) == "search failed"
    else:
        raise AssertionError("Expected the search error to propagate")

    assert client.closed


def test_fastapi_lifespan_creates_and_closes_shared_client(monkeypatch):
    from app import main

    client = FakeClient({"hits": {"hits": []}})
    monkeypatch.setenv("PRODUCT_SEARCH_BACKEND", "opensearch")
    monkeypatch.setattr(main, "create_client", lambda: client)
    app = FastAPI()

    async def exercise_lifespan():
        async with main.lifespan(app):
            assert app.state.opensearch_client is client
            assert not client.closed

        assert app.state.opensearch_client is None
        assert client.closed

    asyncio.run(exercise_lifespan())



def test_search_product_ids_enables_fuzzy_matching_for_long_terms():
    client = FakeClient({"hits": {"hits": []}})

    opensearch_catalog.search_product_ids(
        search="chiken",
        category=None,
        limit=5,
        client=client,
    )

    query = client.calls[0]["body"]["query"]["bool"]
    product_match = query["should"][1]["multi_match"]

    assert product_match["query"] == "chiken"
    assert product_match["fuzziness"] == "AUTO"



def test_search_product_ids_disables_fuzzy_matching_for_short_terms():
    client = FakeClient({"hits": {"hits": []}})

    opensearch_catalog.search_product_ids(
        search="milk",
        category=None,
        limit=5,
        client=client,
    )

    query = client.calls[0]["body"]["query"]["bool"]
    product_match = query["should"][1]["multi_match"]

    assert product_match["query"] == "milk"
    assert "fuzziness" not in product_match


def test_chicken_search_boosts_poultry_subcategory():
    client = FakeClient({"hits": {"hits": []}})

    opensearch_catalog.search_product_ids(
        search="chicken",
        category=None,
        limit=5,
        client=client,
    )

    query = client.calls[0]["body"]["query"]["bool"]
    poultry_boosts = [
        clause
        for clause in query["should"]
        if clause.get("term", {}).get("sub_category.keyword", {}).get("value")
        == "Poultry"
    ]

    assert poultry_boosts, "Chicken search should boost the Poultry subcategory"
    assert poultry_boosts[0]["term"]["sub_category.keyword"]["boost"] > 20
