"""
Tests for the async AI client (mock provider).
"""

import pytest
from app.config import Settings
from app.services.ai.client import AIClient


@pytest.mark.asyncio
async def test_ai_client_mock_returns_metrics() -> None:
    settings = Settings(ai_provider="mock", ai_model="test-model")
    client = AIClient(settings=settings)
    result = await client.complete(user_message="hello world")
    assert "[mock]" in result.content
    assert result.tokens_used >= 1
    assert result.cost_usd >= 0.0
    assert result.latency_ms >= 0.0
