"""
Aggregated return analytics (SQLAlchemy) with pagination and filters.
"""

from datetime import datetime

from fastapi import APIRouter, Query

from app.api.schemas.analytics import AnalyticsPage
from app.dependencies import SessionDep
from app.services.analytics_service import (
    AnalyticsFilters,
    return_rates_by_product,
    return_rates_by_reason,
    return_rates_by_segment,
)

router = APIRouter(prefix="/api/v1/analytics", tags=["analytics"])


@router.get("/returns/by-product", response_model=AnalyticsPage)
async def analytics_by_product(
    session: SessionDep,
    date_from: datetime | None = Query(None),
    date_to: datetime | None = Query(None),
    decision: str | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=200),
) -> AnalyticsPage:
    filters = AnalyticsFilters(date_from=date_from, date_to=date_to, decision=decision)
    offset = (page - 1) * page_size
    rows, total = await return_rates_by_product(session, filters, offset=offset, limit=page_size)
    return AnalyticsPage(rows=rows, total_returns=total, page=page, page_size=page_size)


@router.get("/returns/by-reason", response_model=AnalyticsPage)
async def analytics_by_reason(
    session: SessionDep,
    date_from: datetime | None = Query(None),
    date_to: datetime | None = Query(None),
    decision: str | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=200),
) -> AnalyticsPage:
    filters = AnalyticsFilters(date_from=date_from, date_to=date_to, decision=decision)
    offset = (page - 1) * page_size
    rows, total = await return_rates_by_reason(session, filters, offset=offset, limit=page_size)
    return AnalyticsPage(rows=rows, total_returns=total, page=page, page_size=page_size)


@router.get("/returns/by-segment", response_model=AnalyticsPage)
async def analytics_by_segment(
    session: SessionDep,
    date_from: datetime | None = Query(None),
    date_to: datetime | None = Query(None),
    decision: str | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=200),
) -> AnalyticsPage:
    filters = AnalyticsFilters(date_from=date_from, date_to=date_to, decision=decision)
    offset = (page - 1) * page_size
    rows, total = await return_rates_by_segment(session, filters, offset=offset, limit=page_size)
    return AnalyticsPage(rows=rows, total_returns=total, page=page, page_size=page_size)
