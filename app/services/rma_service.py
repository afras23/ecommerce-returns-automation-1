"""
RMA generation and persistence linked to ``ReturnRequest`` rows.
"""

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.pipeline import AuditLog, ReturnRequest

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class RmaCreateInput:
    """Identifier for the return row receiving an RMA."""

    return_request_id: str


@dataclass(frozen=True)
class RmaCreateOutput:
    """Generated RMA identifiers and timestamps."""

    rma_id: str
    status: str
    return_request_id: str
    created_at: datetime


def generate_rma_id() -> str:
    """Produce a unique RMA identifier (process-local uniqueness)."""
    return f"RMA-{uuid.uuid4().hex[:16].upper()}"


async def create_rma(
    session: AsyncSession,
    data: RmaCreateInput,
) -> RmaCreateOutput:
    """
    Attach a new RMA id to an existing return request and persist audit metadata.

    Args:
        session: Active async DB session.
        data: Target return request primary key.

    Returns:
        RmaCreateOutput with generated RMA id and timestamps.

    Raises:
        ValueError: If the return request does not exist or already has an RMA.
    """
    result = await session.execute(
        select(ReturnRequest).where(ReturnRequest.id == data.return_request_id),
    )
    row = result.scalar_one_or_none()
    if row is None:
        raise ValueError("return_request not found")
    if row.rma_id:
        raise ValueError("return_request already has an RMA")

    rma_id = generate_rma_id()
    while True:
        dup = await session.execute(select(ReturnRequest).where(ReturnRequest.rma_id == rma_id))
        if dup.scalar_one_or_none() is None:
            break
        rma_id = generate_rma_id()

    now = datetime.now(UTC)
    row.rma_id = rma_id
    row.rma_status = "pending"
    row.updated_at = now

    session.add(
        AuditLog(
            entity_type="return_request",
            entity_id=row.id,
            action="rma_created",
            payload_json=f'{{"rma_id":"{rma_id}"}}',
            created_at=now,
        )
    )
    await session.flush()

    logger.info(
        "rma_created",
        extra={"return_request_id": row.id, "rma_id": rma_id},
    )

    return RmaCreateOutput(
        rma_id=rma_id,
        status="pending",
        return_request_id=row.id,
        created_at=now,
    )
