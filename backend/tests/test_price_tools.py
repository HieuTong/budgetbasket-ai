from datetime import date
from types import SimpleNamespace as NS

from fastapi.testclient import TestClient

import app.agent.tools as tools
import app.api.routes.price_intelligence as price_route
from app.agent.agent import BudgetAgent
from app.agent.evals import stub_tools
from app.agent.tracing import AgentTrace
from app.db.session import get_db
from app.main import app
from app.ml.forecasting import PricePoint
from app.services.price_trend import ProductPriceTrend, summarise_for_assistant


def _trend(prices, forecast=None):
    points = [PricePoint(date=date(2026, 9, i + 1), unit_price=p, transaction_count=3) for i, p in enumerate(prices)]
    return ProductPriceTrend(NS(id=2, name="Wholemeal bread"), points, 3 * len(points),
                             forecast or {"trend": "increasing", "forecast_change_percent": 4.0,
                                          "confidence": 0.6, "recommendation": "buy_now"})


def test_summary_reports_facts_and_leaves_out_the_forecasters_recommendation():
    summary = summarise_for_assistant(_trend([3.0, 3.0, 3.2, 3.3, 3.5, 3.6, 3.75]))
    assert summary["change_over_recent_points_percent"] == 25.0  # last 6 points: 3.0 -> 3.75
    assert len(summary["recent_prices"]) == 6
    assert "recommendation" not in summary  # decisions come only from make_product_decision
    assert "not why" in summary["data_note"]


def test_price_trend_tool_handles_missing_product_and_missing_history(monkeypatch):
    monkeypatch.setattr(tools, "load_price_trend", lambda db, pid: None)
    assert "not found" in tools.explain_price_trend_tool(99, db=None)["error"]
    monkeypatch.setattr(tools, "load_price_trend", lambda db, pid: _trend([]))
    assert "No price history" in tools.explain_price_trend_tool(2, db=None)["error"]


def test_find_products_returns_ids_the_agent_can_use(monkeypatch):
    monkeypatch.setattr(tools, "list_catalog", lambda db, search, limit: [
        {"product_id": 7, "name": "Full cream milk 2L", "brand": "Farm", "price": 3.1, "category": "Dairy"}])
    assert tools.find_products_tool("milk", db=None) == [
        {"product_id": 7, "name": "Full cream milk 2L", "brand": "Farm", "price": 3.1}]


def _resp(calls=None, text=""):
    parts = [NS(function_call=NS(name=n, args=a), text=None) for n, a in (calls or [])]
    if text:
        parts.append(NS(function_call=None, text=text))
    return NS(candidates=[NS(content=NS(role="model", parts=parts))], text=text,
              usage_metadata=NS(prompt_token_count=100, candidates_token_count=20))


class Scripted:
    def __init__(self, script):
        self.script = list(script)
        self.models = self

    def generate_content(self, **_):
        return self.script.pop(0)


def test_agent_finds_the_product_then_explains_its_trend():
    script = [_resp([("find_products", {"query": "bread"})]),
              _resp([("explain_price_trend", {"product_id": 2})]),
              _resp(text="Bread rose about 9% over recent weeks.")]
    trace = AgentTrace()
    BudgetAgent(client=Scripted(script), tool_registry=stub_tools()).run(
        "Why is bread more expensive?", {"user_id": 1}, None, trace=trace)
    assert trace.tools_called == ["find_products", "explain_price_trend"]
    assert trace.tool_calls[1].args == {"product_id": 2}


def test_forecast_route_uses_the_shared_loader(monkeypatch):
    app.dependency_overrides[get_db] = lambda: None
    try:
        client = TestClient(app)
        monkeypatch.setattr(price_route, "load_price_trend", lambda db, pid, horizon_weeks=4: _trend([3.0, 3.2]))
        body = client.get("/api/price-intelligence/2/forecast").json()
        assert body["product_name"] == "Wholemeal bread" and body["forecast"]["trend"] == "increasing"
        monkeypatch.setattr(price_route, "load_price_trend", lambda db, pid, horizon_weeks=4: None)
        assert client.get("/api/price-intelligence/99/forecast").status_code == 404
    finally:
        app.dependency_overrides.clear()
