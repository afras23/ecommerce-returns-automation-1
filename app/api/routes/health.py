"""
Liveness and readiness endpoints.
"""

from fastapi import APIRouter, Response
from sqlalchemy import text

from app import database

router = APIRouter(tags=["health"])


@router.get("/health")
async def health() -> dict:
    """Process is up."""
    return {"status": "ok"}


@router.get("/health/ready")
async def ready(response: Response) -> dict:
    """Dependencies (database) are reachable."""
    try:
        async with database.async_session() as session:
            await session.execute(text("SELECT 1"))
        return {"status": "ready", "db": "ok"}
    except Exception as exc:
        response.status_code = 503
        return {"status": "degraded", "db": str(exc)}
