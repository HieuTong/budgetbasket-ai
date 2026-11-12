"""Shared request dependencies."""
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.security import InvalidToken, decode_access_token
from app.db.models import User
from app.db.session import get_db

# auto_error=False so a missing header gives our own 401 instead of FastAPI's default 403.
_bearer = HTTPBearer(auto_error=False)

_UNAUTHORISED = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Not authenticated",
    headers={"WWW-Authenticate": "Bearer"},
)


def _user_from_token(token: str, db: Session) -> User:
    try:
        user_id = decode_access_token(token)
    except InvalidToken:
        raise _UNAUTHORISED
    user = db.get(User, user_id)
    if user is None:
        # A valid token for a deleted account must not keep working.
        raise _UNAUTHORISED
    return user


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
    db: Session = Depends(get_db),
) -> User:
    """The user proven by the request's token. Routes use this instead of a client-sent id."""
    if credentials is None:
        raise _UNAUTHORISED
    return _user_from_token(credentials.credentials, db)


def get_optional_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
    db: Session = Depends(get_db),
) -> User | None:
    """For routes that work for anyone but personalise for signed-in users.

    No token means an anonymous visitor (None). A token that is present but invalid
    is still a 401: silently treating it as anonymous would hide expired sessions
    and broken clients behind generic results.
    """
    if credentials is None:
        return None
    return _user_from_token(credentials.credentials, db)
