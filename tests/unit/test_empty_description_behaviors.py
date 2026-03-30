"""
Empty / minimal text inputs: classification and product condition fallbacks.
"""

import pytest
from app.config import Settings
from app.models.returns import ReturnRecord
from app.services.ai.client import AIClient
from app.services.classification import classify
from app.services.product_condition_service import assess_product_condition


def test_empty_reason_classifies_as_other() -> None:
    record = ReturnRecord(
        order_id="O1",
        reason="",
        preference="refund",
        purchase_date="2026-03-01",
        damaged=False,
    )
    assert classify(record).category == "other"


@pytest.mark.asyncio
async def test_empty_notes_condition_uses_default_fallback() -> None:
    client = AIClient(settings=Settings(ai_provider="mock"))
    result = await assess_product_condition("", ai_client=client)
    assert result.condition.value in (
        "unopened",
        "opened_unused",
        "used",
        "damaged_by_customer",
    )
    assert 0.0 <= result.confidence <= 1.0


@pytest.mark.asyncio
async def test_whitespace_only_notes_still_parses() -> None:
    client = AIClient(settings=Settings(ai_provider="mock"))
    result = await assess_product_condition("   \n\t  ", ai_client=client)
    assert result.condition.value
