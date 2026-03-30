"""
SQLAlchemy aggregate analytics for return rates by product, reason, and segment.

Return *rate* is the share of all matching rows in the filtered window (0–1).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.returns import ReturnRecord


@dataclass(frozen=True)
class AnalyticsFilters:
    """Filter window for analytics queries."""

    date_from: datetime | None = None
    date_to: datetime | None = None
    decision: str | None = None


def _apply_filters(stmt: Any, filters: AnalyticsFilters) -> Any:
    if filters.date_from is not None:
        stmt = stmt.where(ReturnRecord.created_at >= filters.date_from)
    if filters.date_to is not None:
        stmt = stmt.where(ReturnRecord.created_at <= filters.date_to)
    if filters.decision is not None:
        stmt = stmt.where(ReturnRecord.decision == filters.decision)
    return stmt


async def _filtered_total(session: AsyncSession, filters: AnalyticsFilters) -> int:
    stmt = select(func.count(ReturnRecord.id))
    stmt = _apply_filters(stmt, filters)
    result = await session.execute(stmt)
    return int(result.scalar_one())


async def return_rates_by_product(
    session: AsyncSession,
    filters: AnalyticsFilters,
    *,
    offset: int,
    limit: int,
) -> tuple[list[dict[str, Any]], int]:
    """
    Aggregate return counts and rates by product (product_id, else product_type, else unknown).

    Returns:
        (rows, total_matching_returns) where each row has bucket, count, rate.
    """
    total = await _filtered_total(session, filters)
    if total == 0:
        return [], 0

    bucket = func.coalesce(
        ReturnRecord.product_id,
        ReturnRecord.product_type,
        "unknown",
    ).label("bucket")

    agg_subq = (
        _apply_filters(
            select(bucket, func.count(ReturnRecord.id).label("cnt")).select_from(ReturnRecord),
            filters,
        )
        .group_by(bucket)
        .subquery()
    )

    stmt = (
        select(agg_subq.c.bucket, agg_subq.c.cnt)
        .order_by(agg_subq.c.cnt.desc())
        .offset(offset)
        .limit(limit)
    )
    result = await session.execute(stmt)
    rows_out: list[dict[str, Any]] = []
    for bucket_val, cnt in result.all():
        rows_out.append(
            {
                "bucket": str(bucket_val),
                "count": int(cnt),
                "rate": round(int(cnt) / total, 6),
            }
        )
    return rows_out, total


async def return_rates_by_reason(
    session: AsyncSession,
    filters: AnalyticsFilters,
    *,
    offset: int,
    limit: int,
) -> tuple[list[dict[str, Any]], int]:
    """Rates by classification reason (classification_category)."""
    total = await _filtered_total(session, filters)
    if total == 0:
        return [], 0

    bucket = func.coalesce(ReturnRecord.classification_category, "unknown").label("bucket")
    agg_subq = (
        _apply_filters(
            select(bucket, func.count(ReturnRecord.id).label("cnt")).select_from(ReturnRecord),
            filters,
        )
        .group_by(bucket)
        .subquery()
    )

    stmt = (
        select(agg_subq.c.bucket, agg_subq.c.cnt)
        .order_by(agg_subq.c.cnt.desc())
        .offset(offset)
        .limit(limit)
    )
    result = await session.execute(stmt)
    rows_out: list[dict[str, Any]] = []
    for bucket_val, cnt in result.all():
        rows_out.append(
            {
                "bucket": str(bucket_val),
                "count": int(cnt),
                "rate": round(int(cnt) / total, 6),
            }
        )
    return rows_out, total


async def return_rates_by_segment(
    session: AsyncSession,
    filters: AnalyticsFilters,
    *,
    offset: int,
    limit: int,
) -> tuple[list[dict[str, Any]], int]:
    """Rates by customer_segment (or unknown)."""
    total = await _filtered_total(session, filters)
    if total == 0:
        return [], 0

    bucket = func.coalesce(ReturnRecord.customer_segment, "unknown").label("bucket")
    agg_subq = (
        _apply_filters(
            select(bucket, func.count(ReturnRecord.id).label("cnt")).select_from(ReturnRecord),
            filters,
        )
        .group_by(bucket)
        .subquery()
    )

    stmt = (
        select(agg_subq.c.bucket, agg_subq.c.cnt)
        .order_by(agg_subq.c.cnt.desc())
        .offset(offset)
        .limit(limit)
    )
    result = await session.execute(stmt)
    rows_out: list[dict[str, Any]] = []
    for bucket_val, cnt in result.all():
        rows_out.append(
            {
                "bucket": str(bucket_val),
                "count": int(cnt),
                "rate": round(int(cnt) / total, 6),
            }
        )
    return rows_out, total
