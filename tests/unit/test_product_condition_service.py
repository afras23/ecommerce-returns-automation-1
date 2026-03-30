"""
Unit tests for product condition extraction.
"""

from unittest.mock import AsyncMock, patch

import pytest
from app.config import Settings
from app.services.ai.client import AICallResult, AIClient
from app.services.product_condition_service import ProductCondition, assess_product_condition


@pytest.mark.asyncio
async def test_condition_fallback_unopened_keywords() -> None:
    settings = Settings(ai_provider="mock")
    client = AIClient(settings=settings)
    result = await assess_product_condition(
        "Still factory sealed, unopened box",
        ai_client=client,
    )
    assert result.condition == ProductCondition.UNOPENED


@pytest.mark.asyncio
async def test_condition_parses_json() -> None:
    settings = Settings(ai_provider="mock")
    client = AIClient(settings=settings)
    fake = AICallResult(
        content='{"condition":"used","confidence":0.8}',
        tokens_used=5,
        cost_usd=0.0,
        latency_ms=1.0,
    )
    with patch.object(client, "complete", new=AsyncMock(return_value=fake)):
        result = await assess_product_condition("lightly used", ai_client=client)
    assert result.condition == ProductCondition.USED
    assert result.confidence == pytest.approx(0.8)
