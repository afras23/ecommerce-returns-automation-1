"""
FastAPI dependency providers: database sessions and service clients.

Centralizes construction so tests can override with fakes.
"""

from collections.abc import AsyncGenerator
from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app import database
from app.config import settings
from app.services.ai.client import AIClient


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Yield an async SQLAlchemy session per request.

    The session is closed after the request completes.
    Use ``database.async_session`` (not a captured import) so tests can swap
    the engine/session factory on ``app.database``.
    """
    async with database.async_session() as session:
        yield session


def get_ai_client() -> AIClient:
    """
    Return the application AI client (configured model, retries, cost tracking).

    Override in tests with app.dependency_overrides.
    """
    return AIClient(settings=settings)


SessionDep = Annotated[AsyncSession, Depends(get_db_session)]
AIClientDep = Annotated[AIClient, Depends(get_ai_client)]
