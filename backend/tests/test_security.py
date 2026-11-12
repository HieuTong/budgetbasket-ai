import jwt
import pytest

from app.core import security
from app.core.config import settings

SECRET = "test-secret-that-is-at-least-32-chars-long"


@pytest.fixture(autouse=True)
def jwt_secret(monkeypatch):
    monkeypatch.setattr(settings, "JWT_SECRET", SECRET)


def test_password_hash_is_not_the_password_and_verifies():
    hashed = security.hash_password("correct horse")
    assert hashed != "correct horse"
    assert security.verify_password("correct horse", hashed)
    assert not security.verify_password("wrong", hashed)


def test_same_password_hashes_differently_each_time():
    # A random salt means two users with the same password get different hashes.
    assert security.hash_password("same") != security.hash_password("same")


def test_token_round_trip_returns_user_id():
    token = security.create_access_token(42)
    assert security.decode_access_token(token) == 42


def test_expired_token_is_rejected():
    token = security.create_access_token(42, expires_minutes=-1)
    with pytest.raises(security.InvalidToken):
        security.decode_access_token(token)


def test_token_signed_with_another_secret_is_rejected():
    forged = jwt.encode({"sub": "1", "exp": 9999999999}, "x" * 40, algorithm="HS256")
    with pytest.raises(security.InvalidToken):
        security.decode_access_token(forged)


def test_unsigned_token_is_rejected():
    # The classic attack: a token that claims "alg: none" and carries no signature.
    unsigned = jwt.encode({"sub": "1", "exp": 9999999999}, None, algorithm="none")
    with pytest.raises(security.InvalidToken):
        security.decode_access_token(unsigned)


def test_missing_secret_fails_loudly(monkeypatch):
    monkeypatch.setattr(settings, "JWT_SECRET", "")
    with pytest.raises(RuntimeError):
        security.create_access_token(1)
