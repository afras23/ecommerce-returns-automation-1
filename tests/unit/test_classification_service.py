"""
Unit tests for AI return classification parsing and fallbacks.
"""

from unittest.mock import AsyncMock, patch

import pytest
from app.config import Settings
from app.services.ai.client import AICallResult, AIClient
from app.services.classification_service import (
    ReturnReason,
    classify_return_description,
)


@pytest.mark.asyncio
async def test_classification_fallback_keyword_wrong_item() -> None:
    settings = Settings(ai_provider="mock")
    client = AIClient(settings=settings)
    result = await classify_return_description(
        "This is the wrong item, I ordered blue",
        ai_client=client,
    )
    assert result.reason == ReturnReason.WRONG_ITEM
    assert 0.0 <= result.confidence <= 1.0
    assert result.raw


@pytest.mark.asyncio
async def test_classification_parses_valid_ai_json() -> None:
    settings = Settings(ai_provider="mock")
    client = AIClient(settings=settings)
    fake = AICallResult(
        content='{"reason":"defective","confidence":0.91,"raw":"x"}',
        tokens_used=10,
        cost_usd=0.0,
        latency_ms=1.0,
    )
    with patch.object(client, "complete", new=AsyncMock(return_value=fake)):
        result = await classify_return_description("does not power on", ai_client=client)
    assert result.reason == ReturnReason.DEFECTIVE
    assert result.confidence == pytest.approx(0.91)
    assert result.raw == fake.content  # raw model output preserved for audit


@pytest.mark.asyncio
async def test_classification_invalid_json_falls_back() -> None:
    settings = Settings(ai_provider="mock")
    client = AIClient(settings=settings)
    fake = AICallResult(
        content="not-json-at-all {{{",
        tokens_used=1,
        cost_usd=0.0,
        latency_ms=1.0,
    )
    with patch.object(client, "complete", new=AsyncMock(return_value=fake)):
        result = await classify_return_description("changed my mind", ai_client=client)
    assert result.reason == ReturnReason.NO_LONGER_NEEDED
