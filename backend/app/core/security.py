"""Password hashing and access tokens.

Kept in one small module with no database or FastAPI imports, so it can be
unit-tested on its own and reused by routes, scripts and tests.
"""
from datetime import datetime, timedelta, timezone

import jwt
from pwdlib import PasswordHash

from app.core.config import settings

ALGORITHM = "HS256"

# Argon2 is deliberately slow and salted, so a stolen database does not reveal passwords.
_password_hash = PasswordHash.recommended()


class InvalidToken(Exception):
    """The token is missing, expired, tampered with, or malformed."""


def hash_password(password: str) -> str:
    return _password_hash.hash(password)


def verify_password(password: str, hashed: str) -> bool:
    return _password_hash.verify(password, hashed)


def _secret() -> str:
    # Fail loudly rather than sign tokens with an empty key anyone could guess.
    if len(settings.JWT_SECRET) < 32:
        raise RuntimeError("JWT_SECRET must be set to at least 32 characters")
    return settings.JWT_SECRET


def create_access_token(user_id: int, expires_minutes: int | None = None) -> str:
    now = datetime.now(timezone.utc)
    minutes = expires_minutes if expires_minutes is not None else settings.ACCESS_TOKEN_MINUTES
    payload = {
        "sub": str(user_id),                      # who the token is about
        "iat": now,                               # when it was issued
        "exp": now + timedelta(minutes=minutes),  # when it stops working
    }
    return jwt.encode(payload, _secret(), algorithm=ALGORITHM)


def decode_access_token(token: str) -> int:
    """Return the user id inside a valid token, or raise InvalidToken."""
    try:
        payload = jwt.decode(
            token,
            _secret(),
            algorithms=[ALGORITHM],                 # never trust the algorithm named in the token
            options={"require": ["exp", "sub"]},
        )
        return int(payload["sub"])
    except (jwt.PyJWTError, ValueError) as exc:
        raise InvalidToken(str(exc)) from exc
