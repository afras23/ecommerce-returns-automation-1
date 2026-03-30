"""
Request logging and correlation ID middleware.
"""

import logging
import time
import uuid
from collections.abc import Awaitable, Callable
from typing import cast

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.core.context import correlation_id_ctx

logger = logging.getLogger(__name__)


class CorrelationIdMiddleware(BaseHTTPMiddleware):
    """Assign X-Request-ID (or generate), set request.state and contextvar."""

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        header_rid = request.headers.get("x-request-id")
        request_id = header_rid or str(uuid.uuid4())
        request.state.request_id = request_id
        token = correlation_id_ctx.set(request_id)
        try:
            return cast(Response, await call_next(request))
        finally:
            correlation_id_ctx.reset(token)


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Log method, path, status, and duration with structured fields."""

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        start = time.perf_counter()
        response = cast(Response, await call_next(request))
        duration_ms = (time.perf_counter() - start) * 1000
        rid = getattr(request.state, "request_id", None)
        logger.info(
            "http_request",
            extra={
                "request_id": rid,
                "correlation_id": correlation_id_ctx.get(),
                "method": request.method,
                "path": request.url.path,
                "status_code": response.status_code,
                "duration_ms": round(duration_ms, 3),
            },
        )
        return response
