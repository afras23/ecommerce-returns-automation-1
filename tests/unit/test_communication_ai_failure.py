"""
Communication service: AI provider failures propagate (no silent swallowing).
"""

from unittest.mock import AsyncMock

import pytest
from app.config import Settings
from app.core.exceptions import AIProviderError
from app.services.ai.client import AIClient
from app.services.communication_service import (
    draft_manual_review_notification,
    draft_refund_confirmation,
    draft_rejection_message,
)


@pytest.fixture
def failing_client() -> AIClient:
    s = Settings(ai_provider="openai_compatible", ai_api_key="x")
    client = AIClient(settings=s)
    client.complete = AsyncMock(side_effect=AIProviderError("provider unavailable"))
    return client


@pytest.mark.asyncio
async def test_refund_confirmation_raises_on_ai_failure(failing_client: AIClient) -> None:
    with pytest.raises(AIProviderError, match="provider unavailable"):
        await draft_refund_confirmation(
            ai_client=failing_client,
            return_id="ret-1",
            order_id="ORD-1",
            refund_amount_display="$10.00 USD",
            tone="friendly",
        )


@pytest.mark.asyncio
async def test_rejection_message_raises_on_ai_failure(failing_client: AIClient) -> None:
    with pytest.raises(AIProviderError, match="provider unavailable"):
        await draft_rejection_message(
            ai_client=failing_client,
            return_id="ret-1",
            order_id="ORD-1",
            reason_code="outside_window",
            tone="professional",
        )


@pytest.mark.asyncio
async def test_manual_review_raises_on_ai_failure(failing_client: AIClient) -> None:
    with pytest.raises(AIProviderError, match="provider unavailable"):
        await draft_manual_review_notification(
            ai_client=failing_client,
            return_id="ret-1",
            order_id="ORD-1",
            queue_name="tier2_review",
            tone="professional",
        )
