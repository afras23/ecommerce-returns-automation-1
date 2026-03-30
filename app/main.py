"""
FastAPI application entry: middleware, routes, and lifespan hooks.
"""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.middleware import (
    CorrelationIdMiddleware,
    RateLimitMiddleware,
    RequestLoggingMiddleware,
    register_exception_handlers,
)
from app.api.routes import analytics, health, metrics, returns
from app.core.logging import setup_logging
from app.database import init_db


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    await init_db()
    yield


def create_app() -> FastAPI:
    setup_logging()
    application = FastAPI(
        title="Returns Automation API",
        description="Internal ecommerce returns processing system.",
        version="1.0.0",
        lifespan=lifespan,
    )
    register_exception_handlers(application)
    # Order: last registered runs first on incoming requests
    application.add_middleware(RequestLoggingMiddleware)
    application.add_middleware(RateLimitMiddleware)
    application.add_middleware(CorrelationIdMiddleware)

    application.include_router(health.router)
    application.include_router(metrics.router)
    application.include_router(returns.router)
    application.include_router(analytics.router)
    return application


app = create_app()
