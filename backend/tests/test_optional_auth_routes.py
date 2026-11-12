"""Decision and similarity routes: open to everyone, personalised only for the token holder.

The services are replaced by recorders, so each test checks exactly whose purchase
history the route handed over, without depending on what the ML returns.
"""
from datetime import datetime
from types import SimpleNamespace as NS

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import app.api.routes.decision as decision_route
import app.api.routes.similarity as similarity_route
from app.core import security
from app.core.config import settings
from app.db.models import Base, Product, Purchase, User
from app.db.session import get_db
from app.main import app

PATHS = ["/api/decision/10", "/api/similarity/10", "/api/similarity/10/substitutes"]


@pytest.fixture
def seen(monkeypatch):
    """Records the user ids of the purchases each service was given."""
    calls = []

    def record(purchases):
        calls.append(sorted({p.user_id for p in purchases}))

    def fake_decision(product, purchases, products, **_):
        record(purchases)
        return NS(decision=NS(value="BUY"), confidence=0.5, reason="test", price_probability=None)

    def fake_similar(product, products, purchases, top_k):
        record(purchases)
        return []

    monkeypatch.setattr(decision_route, "make_product_decision", fake_decision)
    monkeypatch.setattr(similarity_route, "find_similar_products", fake_similar)
    monkeypatch.setattr(similarity_route, "find_cheaper_substitutes", fake_similar)
    return calls


@pytest.fixture
def client(monkeypatch, seen):
    monkeypatch.setattr(settings, "JWT_SECRET", "test-secret-that-is-at-least-32-chars-long")
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)

    with Session() as db:
        db.add_all([
            User(id=1, name="Alice", email="alice@example.com"),
            User(id=2, name="Bob", email="bob@example.com"),
            Product(id=10, name="Milk", unit_price=3.0, category="Dairy", sub_category="Milk"),
            Purchase(user_id=1, product_id=10, quantity=1, purchased_at=datetime(2026, 9, 1)),
            Purchase(user_id=2, product_id=10, quantity=1, purchased_at=datetime(2026, 9, 2)),
        ])
        db.commit()

    def override_get_db():
        db = Session()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    yield TestClient(app)
    app.dependency_overrides.clear()


def _as(user_id: int) -> dict:
    return {"Authorization": f"Bearer {security.create_access_token(user_id)}"}


@pytest.mark.parametrize("path", PATHS)
def test_anonymous_request_works_and_uses_no_purchase_history(client, seen, path):
    assert client.get(path).status_code == 200
    assert seen == [[]]


@pytest.mark.parametrize("path", PATHS)
def test_signed_in_request_uses_only_that_users_history(client, seen, path):
    assert client.get(path, headers=_as(1)).status_code == 200
    assert seen == [[1]]


@pytest.mark.parametrize("path", PATHS)
def test_user_id_in_the_url_cannot_borrow_another_users_history(client, seen, path):
    # The original bug: ?user_id=2 personalised the answer with Bob's purchases.
    assert client.get(path, params={"user_id": 2}).status_code == 200
    assert client.get(path, params={"user_id": 2}, headers=_as(1)).status_code == 200
    assert seen == [[], [1]]


@pytest.mark.parametrize("path", PATHS)
def test_invalid_token_is_401_not_a_silent_anonymous_fallback(client, seen, path):
    response = client.get(path, headers={"Authorization": "Bearer not-a-token"})
    assert response.status_code == 401
    assert seen == []
