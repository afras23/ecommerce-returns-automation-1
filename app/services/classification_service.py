"""
AI-based return reason classification with Pydantic validation and deterministic fallbacks.
"""

from __future__ import annotations

import json
import logging
import re
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, field_validator

from app.services.ai.client import AIClient
from app.services.ai.prompts import RETURN_REASON_CLASSIFICATION_V2

logger = logging.getLogger(__name__)


class ReturnReason(str, Enum):
    """Canonical return reasons for downstream routing and analytics."""

    DAMAGED = "damaged"
    WRONG_ITEM = "wrong_item"
    NO_LONGER_NEEDED = "no_longer_needed"
    DEFECTIVE = "defective"
    OTHER = "other"


class ClassificationAIResponse(BaseModel):
    """Validated AI JSON payload."""

    reason: ReturnReason
    confidence: float = Field(ge=0.0, le=1.0)
    raw: str = ""

    @field_validator("reason", mode="before")
    @classmethod
    def normalize_reason(cls, value: object) -> str:
        if isinstance(value, ReturnReason):
            return value.value
        s = str(value).strip().lower().replace(" ", "_").replace("-", "_")
        aliases = {
            "buyer_remorse": ReturnReason.NO_LONGER_NEEDED.value,
            "changed_mind": ReturnReason.NO_LONGER_NEEDED.value,
            "not_as_described": ReturnReason.DEFECTIVE.value,
        }
        return aliases.get(s, s)


class ClassificationResult(BaseModel):
    """Public result matching API contract."""

    reason: ReturnReason
    confidence: float
    raw: str

    def model_dump_public(self) -> dict[str, Any]:
        return {
            "reason": self.reason.value,
            "confidence": self.confidence,
            "raw": self.raw,
        }


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


def _keyword_fallback(description: str) -> ClassificationAIResponse:
    low = description.lower()
    if "wrong" in low and "item" in low:
        return ClassificationAIResponse(
            reason=ReturnReason.WRONG_ITEM,
            confidence=0.55,
            raw=description,
        )
    if any(k in low for k in ("defect", "faulty", "not work", "dead on arrival")):
        return ClassificationAIResponse(
            reason=ReturnReason.DEFECTIVE,
            confidence=0.55,
            raw=description,
        )
    if any(k in low for k in ("damaged", "broken", "shattered", "cracked")):
        return ClassificationAIResponse(
            reason=ReturnReason.DAMAGED,
            confidence=0.55,
            raw=description,
        )
    if any(
        k in low
        for k in (
            "no longer",
            "changed my mind",
            "don't need",
            "remorse",
        )
    ):
        return ClassificationAIResponse(
            reason=ReturnReason.NO_LONGER_NEEDED,
            confidence=0.5,
            raw=description,
        )
    return ClassificationAIResponse(
        reason=ReturnReason.OTHER,
        confidence=0.35,
        raw=description,
    )


def _merge_raw(validated: ClassificationAIResponse, description: str) -> ClassificationAIResponse:
    raw = validated.raw.strip() if validated.raw else description
    return validated.model_copy(update={"raw": raw or description})


async def classify_return_description(
    description: str,
    *,
    ai_client: AIClient,
) -> ClassificationResult:
    """
    Classify a customer return description using AI with validation and fallback.

    Args:
        description: Customer-provided return reason text.
        ai_client: Async AI client (mock or live).

    Returns:
        ClassificationResult with reason, confidence, and raw model output text.
    """
    system = RETURN_REASON_CLASSIFICATION_V2
    ai = await ai_client.complete(
        user_message=description,
        system_message=system,
    )
    raw_text = ai.content
    parsed = _extract_json_object(raw_text)
    if parsed is not None:
        if "raw" not in parsed or not parsed.get("raw"):
            parsed["raw"] = description
        try:
            validated = ClassificationAIResponse.model_validate(parsed)
            merged = _merge_raw(validated, description)
            return ClassificationResult(
                reason=merged.reason,
                confidence=merged.confidence,
                raw=raw_text,
            )
        except Exception as exc:
            logger.warning(
                "classification_ai_parse_failed",
                extra={"error": str(exc), "snippet": raw_text[:500]},
            )
    fb = _keyword_fallback(description)
    return ClassificationResult(
        reason=fb.reason,
        confidence=fb.confidence,
        raw=raw_text,
    )
