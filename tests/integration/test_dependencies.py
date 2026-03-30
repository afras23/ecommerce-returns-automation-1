"""
Tests for dependency injection wiring.
"""

import pytest
from app.dependencies import get_ai_client, get_db_session
from app.services.ai.client import AIClient
from sqlalchemy.ext.asyncio import AsyncSession


def test_ai_client_dependency_returns_client() -> None:
    client = get_ai_client()
    assert isinstance(client, AIClient)


@pytest.mark.asyncio
async def test_db_session_generator_yields_session() -> None:
    count = 0
    async for session in get_db_session():
        assert isinstance(session, AsyncSession)
        count += 1
        break
    assert count == 1
