"""
Global exception handlers for consistent JSON error responses.
"""

import logging
import uuid
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.context import correlation_id_ctx
from app.core.exceptions import AppError

logger = logging.getLogger(__name__)


def _error_body(
    *,
    code: str,
    message: str,
    request_id: str | None,
    details: Any | None = None,
) -> dict[str, Any]:
    body: dict[str, Any] = {
        "error": {
            "code": code,
            "message": message,
            "request_id": request_id,
        }
    }
    if details is not None:
        body["error"]["details"] = details
    return body


def register_exception_handlers(app: FastAPI) -> None:
    """Attach handlers for validation, HTTP, app, and unexpected errors."""

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        request: Request,
        exc: RequestValidationError,
    ) -> JSONResponse:
        rid = getattr(request.state, "request_id", None) or str(uuid.uuid4())
        return JSONResponse(
            status_code=422,
            content=_error_body(
                code="VALIDATION_ERROR",
                message="Request validation failed",
                request_id=rid,
                details=exc.errors(),
            ),
        )

    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(
        request: Request,
        exc: StarletteHTTPException,
    ) -> JSONResponse:
        rid = getattr(request.state, "request_id", None) or str(uuid.uuid4())
        detail = exc.detail
        if isinstance(detail, dict):
            message = str(detail.get("message", detail))
        else:
            message = str(detail)
        return JSONResponse(
            status_code=exc.status_code,
            content=_error_body(
                code="HTTP_ERROR",
                message=message,
                request_id=rid,
            ),
        )

    @app.exception_handler(AppError)
    async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
        rid = getattr(request.state, "request_id", None) or str(uuid.uuid4())
        status = 404 if exc.code == "NOT_FOUND" else 400
        return JSONResponse(
            status_code=status,
            content=_error_body(
                code=exc.code,
                message=exc.message,
                request_id=rid,
            ),
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        rid = getattr(request.state, "request_id", None) or str(uuid.uuid4())
        logger.exception(
            "unhandled_exception",
            extra={
                "request_id": rid,
                "correlation_id": correlation_id_ctx.get(),
                "path": request.url.path,
            },
        )
        return JSONResponse(
            status_code=500,
            content=_error_body(
                code="INTERNAL_ERROR",
                message="An unexpected error occurred",
                request_id=rid,
            ),
        )
