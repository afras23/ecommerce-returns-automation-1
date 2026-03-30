"""
AI-assisted product condition assessment with Pydantic validation and safe fallbacks.
"""

from __future__ import annotations

import json
import logging
import re
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, field_validator

from app.services.ai.client import AIClient
from app.services.ai.prompts import PRODUCT_CONDITION_EXTRACTION_V2

logger = logging.getLogger(__name__)


class ProductCondition(str, Enum):
    """Canonical condition labels used by the refund engine."""

    UNOPENED = "unopened"
    OPENED_UNUSED = "opened_unused"
    USED = "used"
    DAMAGED_BY_CUSTOMER = "damaged_by_customer"


class ConditionAIResponse(BaseModel):
    """Validated AI output for condition extraction."""

    condition: ProductCondition
    confidence: float = Field(ge=0.0, le=1.0)

    @field_validator("condition", mode="before")
    @classmethod
    def normalize_condition(cls, value: object) -> str:
        if isinstance(value, ProductCondition):
            return value.value
        s = str(value).strip().lower().replace("-", "_")
        aliases = {
            "damaged": ProductCondition.DAMAGED_BY_CUSTOMER.value,
            "damaged_by_customer": ProductCondition.DAMAGED_BY_CUSTOMER.value,
        }
        return aliases.get(s, s)


class ConditionResult(BaseModel):
    """Final condition assessment exposed to callers."""

    condition: ProductCondition
    confidence: float
    raw: str


def _extract_json_object(text: str) -> dict[str, Any] | None:
    text = text.strip()
    fence = re.search(r"```(?:json)?\s*([\s\S]*?)```", text)
    if fence:
        text = fence.group(1).strip()
    try:
        data = json.loads(text)
        return data if isinstance(data, dict) else None
    except json.JSONDecodeError:
        start = text.find("{")
        end = text.rfind("}")
        if start >= 0 and end > start:
            try:
                data = json.loads(text[start : end + 1])
                return data if isinstance(data, dict) else None
            except json.JSONDecodeError:
                return None
        return None


def _keyword_fallback(notes: str) -> ConditionAIResponse:
    low = notes.lower()
    if any(k in low for k in ("unopened", "sealed", "factory seal", "never opened")):
        return ConditionAIResponse(condition=ProductCondition.UNOPENED, confidence=0.55)
    if any(k in low for k in ("damaged", "scratched", "customer damage", "my fault")):
        return ConditionAIResponse(
            condition=ProductCondition.DAMAGED_BY_CUSTOMER,
            confidence=0.55,
        )
    if any(k in low for k in ("lightly used", "used once", "used")):
        return ConditionAIResponse(condition=ProductCondition.USED, confidence=0.45)
    return ConditionAIResponse(condition=ProductCondition.OPENED_UNUSED, confidence=0.35)


async def assess_product_condition(
    notes: str,
    *,
    ai_client: AIClient,
) -> ConditionResult:
    """
    Extract product condition using the AI client, with Pydantic validation and fallback.

    Args:
        notes: Free-text condition / return notes.
        ai_client: Configured async AI client.

    Returns:
        ConditionResult with condition, confidence, and raw model text.
    """
    system = PRODUCT_CONDITION_EXTRACTION_V2
    result = await ai_client.complete(user_message=notes, system_message=system)
    raw_text = result.content
    parsed = _extract_json_object(raw_text)
    if parsed is not None:
        try:
            validated = ConditionAIResponse.model_validate(parsed)
            return ConditionResult(
                condition=validated.condition,
                confidence=validated.confidence,
                raw=raw_text,
            )
        except Exception as exc:
            logger.warning(
                "condition_ai_parse_failed",
                extra={"error": str(exc), "snippet": raw_text[:500]},
            )
    fb = _keyword_fallback(notes)
    return ConditionResult(
        condition=fb.condition,
        confidence=fb.confidence,
        raw=raw_text,
    )
