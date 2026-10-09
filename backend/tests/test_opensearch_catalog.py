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


def test_search_product_ids_returns_ranked_ids_and_boosts_name(monkeypatch):
    client = FakeClient({
        "hits": {
            "hits": [
                {"_source": {"product_id": 17}},
                {"_source": {"product_id": 4}},
            ]
        }
    })
    monkeypatch.setattr(opensearch_catalog, "_client", lambda: client)

    result = opensearch_catalog.search_product_ids(
        search="Greek yoghurt",
        category="Dairy",
        limit=10,
    )

    assert result == [17, 4]
    request = client.calls[0]
    assert request["index"] == "budgetbasket-products-v1"
    query = request["body"]["query"]["bool"]
    assert query["filter"] == [{"term": {"category.keyword": "Dairy"}}]
    match = query["must"][0]["multi_match"]
    assert match["fields"][0] == "name^5"
    assert match["fuzziness"] == "AUTO"
    assert request["body"]["sort"][0] == {"_score": {"order": "desc"}}
    assert client.closed


def test_search_product_ids_empty_query_uses_stable_id_order(monkeypatch):
    client = FakeClient({
        "hits": {"hits": [{"_source": {"product_id": 2}}, {"_source": {"product_id": 9}}]}
    })
    monkeypatch.setattr(opensearch_catalog, "_client", lambda: client)

    result = opensearch_catalog.search_product_ids(search="  ", category=None, limit=20)

    assert result == [2, 9]
    assert client.calls[0]["body"]["sort"] == [{"product_id": {"order": "asc"}}]


def test_search_product_ids_ignores_hits_without_product_id(monkeypatch):
    client = FakeClient({
        "hits": {"hits": [{ "_source": {} }, {"_source": {"product_id": 3}}]}
    })
    monkeypatch.setattr(opensearch_catalog, "_client", lambda: client)

    assert opensearch_catalog.search_product_ids(search="milk", category=None, limit=5) == [3]
