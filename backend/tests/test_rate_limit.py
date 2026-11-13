import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from starlette.requests import Request

import app.api.routes.chat as chat_route
from app.core import security
from app.core.config import settings
from app.core.rate_limit import SlidingWindowLimiter, client_ip
from app.db.models import Base, User
from app.db.session import get_db
from app.main import app


# --- The limiter itself, with a fake clock so no test has to wait ---------------------

class FakeClock:
    def __init__(self):
        self.now = 1000.0

    def __call__(self):
        return self.now


def test_allows_up_to_the_limit_then_blocks():
    limiter = SlidingWindowLimiter(lambda: 3, 60, clock=FakeClock())
    assert [limiter.check("a") for _ in range(3)] == [None, None, None]
    assert limiter.check("a") is not None


def test_keys_are_counted_separately():
    limiter = SlidingWindowLimiter(lambda: 1, 60, clock=FakeClock())
    assert limiter.check("a") is None
    assert limiter.check("b") is None
    assert limiter.check("a") is not None


def test_retry_after_counts_down_and_the_window_slides():
    clock = FakeClock()
    limiter = SlidingWindowLimiter(lambda: 2, 60, clock=clock)
    limiter.check("a")
    clock.now += 20
    limiter.check("a")
    assert limiter.check("a") == pytest.approx(40)   # first request leaves in 40 s
    clock.now += 41
    assert limiter.check("a") is None                 # one slot is free again
    assert limiter.check("a") is not None             # the second request is still inside


def test_rejected_requests_do_not_extend_the_block():
    clock = FakeClock()
    limiter = SlidingWindowLimiter(lambda: 1, 60, clock=clock)
    limiter.check("a")
    for _ in range(50):
        clock.now += 1
        limiter.check("a")
    clock.now += 11
    assert limiter.check("a") is None


# --- Working out the caller's address ---------------------------------------------------

def _request(forwarded: str | None, peer: str = "10.0.0.1") -> Request:
    headers = [(b"x-forwarded-for", forwarded.encode())] if forwarded else []
    return Request({"type": "http", "headers": headers, "client": (peer, 1234)})


def test_without_a_proxy_the_header_is_ignored(monkeypatch):
    monkeypatch.setattr(settings, "TRUSTED_PROXY_HOPS", 0)
    assert client_ip(_request("1.2.3.4")) == "10.0.0.1"


def test_behind_one_proxy_the_last_entry_is_used_so_spoofing_fails(monkeypatch):
    monkeypatch.setattr(settings, "TRUSTED_PROXY_HOPS", 1)
    # The caller wrote "9.9.9.9"; the proxy appended the real address after it.
    assert client_ip(_request("9.9.9.9, 203.0.113.7")) == "203.0.113.7"


def test_missing_header_falls_back_to_the_connection(monkeypatch):
    monkeypatch.setattr(settings, "TRUSTED_PROXY_HOPS", 1)
    assert client_ip(_request(None)) == "10.0.0.1"


# --- The routes ---------------------------------------------------------------------------

@pytest.fixture
def client(monkeypatch):
    monkeypatch.setattr(settings, "JWT_SECRET", "test-secret-that-is-at-least-32-chars-long")
    monkeypatch.setattr(settings, "TRUSTED_PROXY_HOPS", 1)
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

    class FakeAgent:
        calls = 0

        def run(self, *args, **kwargs):
            FakeAgent.calls += 1
            return "ok"

    monkeypatch.setattr(chat_route, "BudgetAgent", FakeAgent)
    monkeypatch.setattr(chat_route, "build_basket_candidates", lambda db, user_id: ([], 0))

    app.dependency_overrides[get_db] = override_get_db
    test_client = TestClient(app)
    test_client.agent = FakeAgent
    yield test_client
    app.dependency_overrides.clear()


def _chat(client, ip="203.0.113.7", token=True):
    headers = {"X-Forwarded-For": ip}
    if token:
        headers["Authorization"] = f"Bearer {security.create_access_token(1)}"
    return client.post("/api/chat/", json={"message": "hello"}, headers=headers)


def test_chat_is_limited_per_address_and_says_when_to_retry(client, monkeypatch):
    monkeypatch.setattr(settings, "CHAT_REQUESTS_PER_MINUTE", 3)
    assert [_chat(client).status_code for _ in range(3)] == [200, 200, 200]

    blocked = _chat(client)
    assert blocked.status_code == 429
    assert int(blocked.headers["retry-after"]) >= 1
    assert client.agent.calls == 3            # the model was never called for the 4th

    assert _chat(client, ip="198.51.100.9").status_code == 200   # another visitor is unaffected


def test_daily_cap_is_shared_across_addresses(client, monkeypatch):
    monkeypatch.setattr(settings, "CHAT_REQUESTS_PER_DAY", 2)
    assert _chat(client, ip="198.51.100.1").status_code == 200
    assert _chat(client, ip="198.51.100.2").status_code == 200
    assert _chat(client, ip="198.51.100.3").status_code == 429


def test_requests_without_a_token_cannot_use_up_the_daily_cap(client, monkeypatch):
    monkeypatch.setattr(settings, "CHAT_REQUESTS_PER_DAY", 1)
    for _ in range(5):
        assert _chat(client, token=False).status_code == 401
    assert _chat(client).status_code == 200


def test_login_attempts_are_limited_per_address(client, monkeypatch):
    monkeypatch.setattr(settings, "AUTH_REQUESTS_PER_MINUTE", 3)
    attempt = lambda: client.post(
        "/api/auth/login",
        json={"email": "seeded@example.com", "password": "guess"},
        headers={"X-Forwarded-For": "203.0.113.7"},
    )
    assert [attempt().status_code for _ in range(3)] == [401, 401, 401]
    assert attempt().status_code == 429
