"""
Simple in-memory token bucket rate limiter per client key (IP or forwarded for).

Suitable for single-instance deployments; replace with Redis for multi-node.
"""

import logging
import time
from collections.abc import Awaitable, Callable
from typing import cast

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from starlette.types import ASGIApp

from app.config import settings

logger = logging.getLogger(__name__)


class _TokenBucket:
    """Token bucket with refill rate per second."""

    def __init__(self, capacity: float, refill_per_second: float) -> None:
        self.capacity = capacity
        self.refill_per_second = refill_per_second
        self.tokens = capacity
        self.last = time.monotonic()

    def consume(self, amount: float = 1.0) -> bool:
        now = time.monotonic()
        elapsed = now - self.last
        self.last = now
        self.tokens = min(self.capacity, self.tokens + elapsed * self.refill_per_second)
        if self.tokens >= amount:
            self.tokens -= amount
            return True
        return False


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Return 429 when the client exceeds configured requests per minute."""

    def __init__(self, app: ASGIApp, requests_per_minute: int | None = None) -> None:
        super().__init__(app)
        rpm = requests_per_minute
        if rpm is None:
            rpm = settings.rate_limit_requests_per_minute
        capacity = float(max(1, rpm))
        refill = capacity / 60.0
        self._buckets: dict[str, _TokenBucket] = {}
        self._capacity = capacity
        self._refill = refill

    def _bucket_for(self, client_key: str) -> _TokenBucket:
        if client_key not in self._buckets:
            self._buckets[client_key] = _TokenBucket(self._capacity, self._refill)
        return self._buckets[client_key]

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        forwarded = request.headers.get("x-forwarded-for")
        if forwarded:
            client_key = forwarded.split(",")[0].strip()
        else:
            client_key = request.client.host if request.client else "unknown"

        bucket = self._bucket_for(client_key)
        if not bucket.consume(1.0):
            logger.warning(
                "rate_limit_exceeded",
                extra={"client_key": client_key, "path": request.url.path},
            )
            return JSONResponse(
                status_code=429,
                content={
                    "error": {
                        "code": "RATE_LIMITED",
                        "message": "Too many requests",
                        "request_id": getattr(request.state, "request_id", None),
                    }
                },
            )

        return cast(Response, await call_next(request))
