from types import SimpleNamespace as NS

from fastapi.testclient import TestClient

import app.services.basket as basket_service
from app.db.session import get_db
from app.main import app


def test_basket_response_reports_where_time_was_spent(monkeypatch):
    products = [NS(id=i, name=f"item {i}", unit_price=2.0 + i, category="Pantry", sub_category="Misc")
                for i in range(1, 6)]
    monkeypatch.setattr(basket_service, "list_basket_products", lambda db: products)
    monkeypatch.setattr(basket_service, "get_user_purchases", lambda db, user_id: [])
    app.dependency_overrides[get_db] = lambda: None
    try:
        response = TestClient(app).post("/api/basket/optimize", json={"user_id": 1, "budget": 10})
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    stages = [part.split(";")[0].strip() for part in response.headers["server-timing"].split(",")]
    assert stages == ["load", "score", "solve"]
