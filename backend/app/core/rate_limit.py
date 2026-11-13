"""Request rate limiting.

A sliding-window limiter held in memory. That is correct for one server process, which
is how this app is deployed. With several processes or servers each would count
separately, and the counters would need to move to a shared store such as Redis.
"""
import threading
import time
from collections import deque
from typing import Callable

from fastapi import Depends, HTTPException, Request, status

from app.api.deps import get_current_user
from app.core.config import settings
from app.db.models import User


class SlidingWindowLimiter:
    """Allows at most `limit` requests per key in any `window_seconds` period."""

    def __init__(
        self,
        limit: Callable[[], int],
        window_seconds: float,
        clock: Callable[[], float] = time.monotonic,
    ):
        self._limit = limit
        self._window = window_seconds
        self._clock = clock
        self._hits: dict[str, deque[float]] = {}
        # Route handlers run on several threads, so the counters need a lock.
        self._lock = threading.Lock()

    def check(self, key: str) -> float | None:
        """Record a request. Returns None if allowed, else seconds until the next slot."""
        now = self._clock()
        cutoff = now - self._window

        with self._lock:
            hits = self._hits.setdefault(key, deque())
            while hits and hits[0] <= cutoff:
                hits.popleft()

            if len(hits) >= self._limit():
                # Rejected requests are not recorded, so hammering does not extend the block.
                return hits[0] + self._window - now

            hits.append(now)
            self._forget_idle_keys(cutoff)
            return None

    def _forget_idle_keys(self, cutoff: float) -> None:
        # Without this the dictionary would grow by one entry per visitor, forever.
        if len(self._hits) < 10_000:
            return
        for key in [k for k, hits in self._hits.items() if not hits or hits[-1] <= cutoff]:
            del self._hits[key]

    def reset(self) -> None:
        with self._lock:
            self._hits.clear()


def client_ip(request: Request) -> str:
    """The caller's address, for per-visitor limits.

    Behind a proxy the direct connection is the proxy, and the real address is in
    X-Forwarded-For. A caller can put anything at the start of that header, so only
    the entries added by our own proxies (counted from the right) are trusted.
    """
    hops = settings.TRUSTED_PROXY_HOPS
    if hops > 0:
        forwarded = [
            part.strip()
            for part in request.headers.get("x-forwarded-for", "").split(",")
            if part.strip()
        ]
        if len(forwarded) >= hops:
            return forwarded[-hops]
    return request.client.host if request.client else "unknown"


chat_per_ip = SlidingWindowLimiter(lambda: settings.CHAT_REQUESTS_PER_MINUTE, 60)
chat_per_day = SlidingWindowLimiter(lambda: settings.CHAT_REQUESTS_PER_DAY, 24 * 60 * 60)
auth_per_ip = SlidingWindowLimiter(lambda: settings.AUTH_REQUESTS_PER_MINUTE, 60)

ALL_LIMITERS = (chat_per_ip, chat_per_day, auth_per_ip)


def _too_many(retry_after: float, detail: str) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        detail=detail,
        # Tells well-behaved clients how long to wait before trying again.
        headers={"Retry-After": str(max(1, int(retry_after) + 1))},
    )


def limit_auth(request: Request) -> None:
    """Slows password guessing and sign-up floods from one address."""
    retry_after = auth_per_ip.check(client_ip(request))
    if retry_after is not None:
        raise _too_many(retry_after, "Too many attempts. Please wait a moment.")


def limit_chat(
    request: Request,
    user: User = Depends(get_current_user),
) -> User:
    """Signed-in user for a chat request, after the rate limits.

    Order matters. Authentication runs first (it is a sub-dependency), so requests
    without a token never touch the shared daily budget. The per-address limit runs
    next, so one noisy visitor is stopped before they can use up that budget.
    Per-address rather than per-user, because every visitor shares the demo account.
    """
    retry_after = chat_per_ip.check(client_ip(request))
    if retry_after is not None:
        raise _too_many(retry_after, "You're sending messages too quickly. Please wait a moment.")

    retry_after = chat_per_day.check("everyone")
    if retry_after is not None:
        raise _too_many(retry_after, "The assistant has reached its daily limit. Please try again tomorrow.")

    return user
