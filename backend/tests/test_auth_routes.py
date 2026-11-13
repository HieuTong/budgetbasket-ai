import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core import security
from app.core.config import settings
from app.db.models import Base, User
from app.db.session import get_db
from app.main import app


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setattr(settings, "JWT_SECRET", "test-secret-that-is-at-least-32-chars-long")
    # One in-memory database shared across threads, rebuilt for every test.
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)

    with Session() as db:
        db.add(User(id=1, name="Demo User 1", email="seeded@example.com"))
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


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def _register(client, email="hieu@example.com", password="a-strong-password"):
    return client.post("/api/auth/register", json={"email": email, "password": password})


def test_register_then_me_returns_the_new_user(client):
    resp = _register(client)
    assert resp.status_code == 201
    me = client.get("/api/auth/me", headers=_auth(resp.json()["access_token"]))
    assert me.status_code == 200
    assert me.json()["email"] == "hieu@example.com"


def test_response_never_contains_the_password_or_hash(client):
    token = _register(client).json()["access_token"]
    body = client.get("/api/auth/me", headers=_auth(token)).text
    assert "password" not in body


def test_duplicate_email_is_rejected_even_with_different_case(client):
    assert _register(client).status_code == 201
    assert _register(client, email="HIEU@example.com").status_code == 409


def test_short_password_is_rejected(client):
    assert _register(client, password="short").status_code == 422


def test_login_with_correct_password(client):
    _register(client)
    resp = client.post("/api/auth/login",
                       json={"email": "hieu@example.com", "password": "a-strong-password"})
    assert resp.status_code == 200
    assert security.decode_access_token(resp.json()["access_token"]) > 0


def test_wrong_password_and_unknown_email_look_identical(client):
    _register(client)
    wrong = client.post("/api/auth/login",
                        json={"email": "hieu@example.com", "password": "wrong-password"})
    unknown = client.post("/api/auth/login",
                          json={"email": "nobody@example.com", "password": "wrong-password"})
    assert wrong.status_code == unknown.status_code == 401
    assert wrong.json() == unknown.json()


def test_seeded_account_without_a_password_cannot_log_in(client):
    with_any_password = client.post(
        "/api/auth/login",
        json={"email": "seeded@example.com", "password": "anything"},
    )
    assert with_any_password.status_code == 401


def test_demo_login_signs_in_as_the_demo_user(client):
    resp = client.post("/api/auth/demo")
    assert resp.status_code == 200
    me = client.get("/api/auth/me", headers=_auth(resp.json()["access_token"]))
    assert me.json()["id"] == settings.DEMO_USER_ID


def test_me_without_a_token_is_401(client):
    resp = client.get("/api/auth/me")
    assert resp.status_code == 401
    assert resp.headers["www-authenticate"] == "Bearer"


def test_me_with_a_garbage_token_is_401(client):
    assert client.get("/api/auth/me", headers=_auth("not-a-token")).status_code == 401


def test_token_for_a_deleted_user_is_401(client):
    token = security.create_access_token(999)
    assert client.get("/api/auth/me", headers=_auth(token)).status_code == 401
