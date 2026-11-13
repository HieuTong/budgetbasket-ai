"""Shared test setup."""
import pytest

from app.api.deps import get_current_user
from app.core.rate_limit import ALL_LIMITERS
from app.db.models import User
from app.main import app

# These modules test what happens AFTER login (chat, basket), with the database faked out.
# They run as a signed-in user so they stay focused on that behaviour.
# Every other test goes through real authentication, which is the safe default.
SIGNED_IN_MODULES = {"test_chat_route", "test_chat_memory", "test_basket_timing"}


@pytest.fixture(autouse=True)
def fresh_rate_limits():
    # The counters live in memory for the whole test run. Without a reset, requests
    # made by one test would count against the next and cause random 429 failures.
    for limiter in ALL_LIMITERS:
        limiter.reset()
    yield


@pytest.fixture(autouse=True)
def signed_in_for_listed_modules(request):
    if request.module.__name__.split(".")[-1] not in SIGNED_IN_MODULES:
        yield
        return
    app.dependency_overrides[get_current_user] = lambda: User(id=1, name="Test User")
    yield
    app.dependency_overrides.pop(get_current_user, None)
