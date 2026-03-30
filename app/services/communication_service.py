"""
AI-drafted customer communications using strict FACTS blocks (no invented amounts).

Templates live in ``app.services.ai.prompts``; amounts must be supplied by callers only.
"""

from __future__ import annotations

import logging
from typing import Literal

from app.core.context import correlation_id_ctx
from app.services.ai.client import AIClient
from app.services.ai.prompts import (
    COMMUNICATION_MANUAL_REVIEW_V1,
    COMMUNICATION_REFUND_CONFIRMATION_V1,
    COMMUNICATION_REJECTION_V1,
)

logger = logging.getLogger(__name__)

Tone = Literal["friendly", "professional"]


def _facts_block(**facts: str) -> str:
    lines = ["FACTS (do not alter numbers or ids; do not invent new ones):"]
    for key, value in facts.items():
        lines.append(f"- {key}: {value}")
    return "\n".join(lines)


async def draft_refund_confirmation(
    *,
    ai_client: AIClient,
    return_id: str,
    order_id: str,
    refund_amount_display: str,
    tone: Tone = "professional",
) -> str:
    """
    Generate refund confirmation copy.

    ``refund_amount_display`` must be pre-formatted by the caller.
    """
    system = COMMUNICATION_REFUND_CONFIRMATION_V1.format(tone=tone)
    user = _facts_block(
        return_id=return_id,
        order_id=order_id,
        refund_amount=refund_amount_display,
    )
    result = await ai_client.complete(system_message=system, user_message=user)
    logger.info(
        "communication_refund_confirmation",
        extra={
            "correlation_id": correlation_id_ctx.get(),
            "return_id": return_id,
            "tone": tone,
        },
    )
    return result.content.strip()


async def draft_rejection_message(
    *,
    ai_client: AIClient,
    return_id: str,
    order_id: str,
    reason_code: str,
    tone: Tone = "professional",
) -> str:
    """Generate rejection copy using policy reason codes only (no dollar amounts)."""
    system = COMMUNICATION_REJECTION_V1.format(tone=tone)
    user = _facts_block(
        return_id=return_id,
        order_id=order_id,
        reason_code=reason_code,
    )
    result = await ai_client.complete(system_message=system, user_message=user)
    logger.info(
        "communication_rejection",
        extra={
            "correlation_id": correlation_id_ctx.get(),
            "return_id": return_id,
            "tone": tone,
        },
    )
    return result.content.strip()


async def draft_manual_review_notification(
    *,
    ai_client: AIClient,
    return_id: str,
    order_id: str,
    queue_name: str,
    tone: Tone = "professional",
) -> str:
    """Notify customer their return is under manual review (no refund promise)."""
    system = COMMUNICATION_MANUAL_REVIEW_V1.format(tone=tone)
    user = _facts_block(
        return_id=return_id,
        order_id=order_id,
        queue=queue_name,
    )
    result = await ai_client.complete(system_message=system, user_message=user)
    logger.info(
        "communication_manual_review",
        extra={
            "correlation_id": correlation_id_ctx.get(),
            "return_id": return_id,
            "tone": tone,
        },
    )
    return result.content.strip()
