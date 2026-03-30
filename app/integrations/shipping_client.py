"""
Shipping integration stub: label generation and persistence on a return row.

Links the generated label JSON to the return id (RMA correlation).
"""

from __future__ import annotations

import json
import logging
import uuid

from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.returns import ReturnRecord

logger = logging.getLogger(__name__)


def generate_label(return_id: str) -> dict:
    """
    Create a shipping label for the given return (mock implementation).

    Args:
        return_id: Internal return identifier.

    Returns:
        Dict with mock label metadata (tracking id, carrier, label URL placeholder).
    """
    tracking = f"MOCK-{uuid.uuid4().hex[:12].upper()}"
    payload = {
        "return_id": return_id,
        "carrier": "mock_carrier",
        "tracking_number": tracking,
        "label_url": f"https://example.com/labels/{return_id}",
        "status": "created",
    }
    logger.info(
        "shipping_label_generated",
        extra={"return_id": return_id, "tracking_number": tracking},
    )
    return payload


async def attach_label_to_return(
    session: AsyncSession,
    *,
    return_id: str,
) -> dict:
    """
    Generate a mock label and persist JSON on the return row (links label to RMA/return id).

    Args:
        session: Active async session.
        return_id: Primary key of ``ReturnRecord``.

    Returns:
        Label payload dict stored in ``shipping_label_json``.
    """
    label = generate_label(return_id)
    await session.execute(
        update(ReturnRecord)
        .where(ReturnRecord.id == return_id)
        .values(shipping_label_json=json.dumps(label)),
    )
    logger.info(
        "shipping_label_attached",
        extra={"return_id": return_id, "tracking_number": label.get("tracking_number")},
    )
    return label
