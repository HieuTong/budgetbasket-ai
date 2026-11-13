"""Proves the fix: a user can only ever reach their own data.

Uses a real (in-memory) database with two users, so the tests exercise the same
token -> user -> query path as production.
"""
from datetime import datetime

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core import security
from app.core.config import settings
from app.db.models import Base, Product, Purchase, User
from app.db.session import get_db
from app.main import app


@pytest.fixture
def client(monkeypatch):
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
            Product(id=10, name="Alice's milk", unit_price=3.0, category="Dairy", sub_category="Milk"),
            Product(id=20, name="Bob's bread", unit_price=4.0, category="Bakery", sub_category="Bread"),
            Purchase(user_id=1, product_id=10, quantity=1, purchased_at=datetime(2026, 9, 1)),
            Purchase(user_id=2, product_id=20, quantity=1, purchased_at=datetime(2026, 9, 2)),
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


@pytest.mark.parametrize("method,path,body", [
    ("get", "/api/purchases/me", None),
    ("get", "/api/purchase-profile/me", None),
    ("post", "/api/basket/optimize", {"budget": 20}),
    ("post", "/api/chat/", {"message": "hello"}),
])
def test_protected_routes_reject_requests_without_a_token(client, method, path, body):
    response = client.request(method, path, json=body)
    assert response.status_code == 401


def test_each_user_sees_only_their_own_purchases(client):
    alice = client.get("/api/purchases/me", headers=_as(1)).json()
    bob = client.get("/api/purchases/me", headers=_as(2)).json()
    assert [p["name"] for p in alice] == ["Alice's milk"]
    assert [p["name"] for p in bob] == ["Bob's bread"]


def test_old_urls_with_a_user_id_no_longer_exist(client):
    # The original bug: anyone could read user 2's data by putting 2 in the URL.
    assert client.get("/api/purchases/2", headers=_as(1)).status_code == 404
    assert client.get("/api/purchase-profile/2", headers=_as(1)).status_code == 404


def test_profile_belongs_to_the_token_holder(client):
    profile = client.get("/api/purchase-profile/me", headers=_as(2)).json()
    assert profile["user_id"] == 2


def test_user_id_in_the_request_body_is_ignored(client):
    # Alice claims to be Bob in the body. The server must still treat her as Alice.
    response = client.post(
        "/api/basket/optimize",
        json={"user_id": 2, "budget": 20},
        headers=_as(1),
    )
    assert response.status_code == 200
    assert response.json()["user_id"] == 1
