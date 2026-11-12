from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.config import settings
from app.core.security import create_access_token, hash_password, verify_password
from app.db.models import User
from app.db.session import get_db

router = APIRouter()

# Verified when the email is unknown, so "no such user" takes as long as "wrong password".
_DUMMY_HASH = hash_password("not-a-real-password")


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    name: str | None = Field(default=None, max_length=100)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserResponse(BaseModel):
    id: int
    name: str | None
    email: str | None


def _normalise(email: str) -> str:
    # One account per address, however the user types it.
    return email.strip().lower()


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
def register(req: RegisterRequest, db: Session = Depends(get_db)):
    user = User(
        email=_normalise(req.email),
        name=req.name,
        password_hash=hash_password(req.password),
    )
    db.add(user)
    try:
        # Let the unique index decide. Checking first and inserting second
        # would let two simultaneous requests both pass the check.
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, "Email already registered")
    return TokenResponse(access_token=create_access_token(user.id))


@router.post("/login", response_model=TokenResponse)
def login(req: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == _normalise(req.email)).first()
    stored_hash = user.password_hash if user and user.password_hash else _DUMMY_HASH
    password_ok = verify_password(req.password, stored_hash)

    if user is None or not user.password_hash or not password_ok:
        # One message for every failure, so the reply never reveals which emails exist.
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED,
            "Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return TokenResponse(access_token=create_access_token(user.id))


@router.post("/demo", response_model=TokenResponse)
def demo_login(db: Session = Depends(get_db)):
    """Sign a visitor into the seeded demo account, with a shorter-lived token."""
    user = db.get(User, settings.DEMO_USER_ID)
    if user is None:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "Demo account is not set up")
    return TokenResponse(
        access_token=create_access_token(user.id, expires_minutes=settings.DEMO_TOKEN_MINUTES)
    )


@router.get("/me", response_model=UserResponse)
def me(user: User = Depends(get_current_user)):
    return UserResponse(id=user.id, name=user.name, email=user.email)
