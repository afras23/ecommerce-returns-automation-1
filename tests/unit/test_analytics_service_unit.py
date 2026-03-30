"""
Direct analytics_service aggregate queries against an isolated async SQLite session.
"""

import pytest
from app.models.returns import Base, ReturnRecord
from app.services.analytics_service import (
    AnalyticsFilters,
    return_rates_by_product,
    return_rates_by_reason,
    return_rates_by_segment,
)
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool


@pytest.fixture
async def analytics_session() -> AsyncSession:
    engine = create_async_engine(
        "sqlite+aiosqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    Session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with Session() as session:
        session.add_all(
            [
                ReturnRecord(
                    order_id="A",
                    reason="r",
                    preference="refund",
                    purchase_date="2026-03-01",
                    product_id="SKU-A",
                    classification_category="buyer_remorse",
                    customer_segment="retail",
                ),
                ReturnRecord(
                    order_id="B",
                    reason="r",
                    preference="refund",
                    purchase_date="2026-03-01",
                    product_id="SKU-B",
                    classification_category="buyer_remorse",
                    customer_segment="wholesale",
                ),
            ]
        )
        await session.commit()

    async with Session() as read_session:
        yield read_session

    await engine.dispose()


@pytest.mark.asyncio
async def test_return_rates_by_product_totals_and_buckets(analytics_session: AsyncSession) -> None:
    rows, total = await return_rates_by_product(
        analytics_session,
        AnalyticsFilters(),
        offset=0,
        limit=10,
    )
    assert total == 2
    buckets = {r["bucket"] for r in rows}
    assert buckets >= {"SKU-A", "SKU-B"}


@pytest.mark.asyncio
async def test_return_rates_by_reason(analytics_session: AsyncSession) -> None:
    rows, total = await return_rates_by_reason(
        analytics_session,
        AnalyticsFilters(),
        offset=0,
        limit=10,
    )
    assert total == 2
    assert any(r["bucket"] == "buyer_remorse" for r in rows)


@pytest.mark.asyncio
async def test_return_rates_by_segment(analytics_session: AsyncSession) -> None:
    rows, total = await return_rates_by_segment(
        analytics_session,
        AnalyticsFilters(),
        offset=0,
        limit=10,
    )
    assert total == 2
    assert {r["bucket"] for r in rows} >= {"retail", "wholesale"}


@pytest.mark.asyncio
async def test_analytics_filter_decision_excludes_mismatch(analytics_session: AsyncSession) -> None:
    rows, total = await return_rates_by_product(
        analytics_session,
        AnalyticsFilters(decision="rejected"),
        offset=0,
        limit=10,
    )
    assert total == 0
    assert rows == []
