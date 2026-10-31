"""End-to-end tests through the real API routes, with the database and the LLM replaced by fakes.

These would have caught the bug where chat sent the optimiser an empty product list:
the agent evaluation supplied products itself, so it never exercised the real route.
"""
from types import SimpleNamespace as NS

import pytest
from fastapi.testclient import TestClient

import app.api.routes.chat as chat_route
import app.services.basket as basket_service
from app.agent.agent import BudgetAgent
from app.agent.evals import stub_tools
from app.agent.tools import run_budget_optimizer_tool
from app.db.session import get_db
from app.main import app

PRODUCTS = [
    NS(id=1, name="Full cream milk 2L", unit_price=3.10, category="Dairy", sub_category="Milk"),
    NS(id=2, name="Wholemeal bread", unit_price=3.80, category="Bakery", sub_category="Bread"),
    NS(id=3, name="Free range eggs 12", unit_price=6.50, category="Dairy", sub_category="Eggs"),
    NS(id=4, name="Bananas 1kg", unit_price=3.90, category="Produce", sub_category="Fruit"),
]


def _resp(calls=None, text=""):
    parts = [NS(function_call=NS(name=n, args=a), text=None) for n, a in (calls or [])]
    if text:
        parts.append(NS(function_call=None, text=text))
    return NS(candidates=[NS(content=NS(role="model", parts=parts))], text=text,
              usage_metadata=NS(prompt_token_count=100, candidates_token_count=20))


class RecordingClient:
    """Scripted fake model that also records every prompt it was sent."""

    def __init__(self, script):
        self.script, self.prompts = list(script), []
        self.models = self

    def generate_content(self, contents, **_):
        self.prompts.append(str(contents[0].parts[0].text))
        return self.script.pop(0)


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setattr(basket_service, "list_basket_products", lambda db: PRODUCTS)
    monkeypatch.setattr(basket_service, "get_user_purchases", lambda db, user_id: [])
    app.dependency_overrides[get_db] = lambda: None
    yield TestClient(app)
    app.dependency_overrides.clear()


def test_chat_optimiser_receives_the_users_real_products(client, monkeypatch):
    results = []

    def recording_optimizer(**kwargs):
        result = run_budget_optimizer_tool(**kwargs)
        results.append(result)
        return result

    fake = RecordingClient([_resp([("run_budget_optimizer", {"budget": 10})]), _resp(text="Here you go.")])
    tools = {**stub_tools(), "run_budget_optimizer": recording_optimizer}
    monkeypatch.setattr(chat_route, "BudgetAgent", lambda: BudgetAgent(client=fake, tool_registry=tools))

    response = client.post("/api/chat/", json={"user_id": 1, "message": "Build me a $10 basket"})

    assert response.status_code == 200 and response.json()["reply"] == "Here you go."
    [basket] = results
    assert basket["items"], "the optimiser got an empty product list"
    assert basket["total_cost"] <= 10


def test_prompt_shows_a_product_count_not_the_catalogue(client, monkeypatch):
    fake = RecordingClient([_resp(text="Hi!")])
    monkeypatch.setattr(chat_route, "BudgetAgent", lambda: BudgetAgent(client=fake, tool_registry=stub_tools()))

    client.post("/api/chat/", json={"user_id": 1, "message": "Hello"})

    prompt = fake.prompts[0]
    assert '"candidate_product_count": 4' in prompt
    assert "Wholemeal bread" not in prompt


def test_basket_page_and_chat_use_the_same_candidates(client):
    page = client.post("/api/basket/optimize", json={"user_id": 1, "budget": 10}).json()
    assert page["candidate_count"] == len(PRODUCTS)
    assert page["total_cost"] <= 10 and page["items"]
    candidates, _ = basket_service.build_basket_candidates(None, 1)
    assert {c.product_id for c in candidates} == {p.id for p in PRODUCTS}
