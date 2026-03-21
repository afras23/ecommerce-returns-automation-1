from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI

from app.core.metrics import metrics
from app.database import init_db
from app.routes import health, returns


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    await init_db()
    yield


app = FastAPI(
    title="Returns Automation API",
    description="Internal ecommerce returns processing system.",
    version="1.0.0",
    lifespan=lifespan,
)

app.include_router(health.router)
app.include_router(returns.router)


@app.get("/metrics", tags=["observability"])
async def get_metrics() -> dict:
    return metrics.snapshot()
