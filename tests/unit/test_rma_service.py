"""
Unit tests for RMA generation and DB linkage.
"""

import app.models.pipeline  # noqa: F401
import pytest
from app.models.pipeline import Customer, ReturnRequest
from app.models.returns import Base
from app.services.rma_service import RmaCreateInput, create_rma, generate_rma_id
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine


@pytest.mark.asyncio
async def test_generate_rma_id_unique() -> None:
    ids = {generate_rma_id() for _ in range(50)}
    assert len(ids) == 50


@pytest.mark.asyncio
async def test_create_rma_persists_and_is_idempotent_error() -> None:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    Session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with Session() as session:
        cust = Customer(external_customer_id="ext-1", email="a@b.c")
        session.add(cust)
        await session.flush()
        rr = ReturnRequest(
            customer_id=cust.id,
            order_id="ORD-1",
            description="test",
            order_amount=10.0,
            status="pending",
        )
        session.add(rr)
        await session.commit()
        rid = rr.id

    async with Session() as session:
        out = await create_rma(session, RmaCreateInput(return_request_id=rid))
        assert out.rma_id.startswith("RMA-")
        assert out.status == "pending"
        await session.commit()

    async with Session() as session:
        q = await session.execute(select(ReturnRequest).where(ReturnRequest.id == rid))
        row = q.scalar_one()
        assert row.rma_id == out.rma_id
        assert row.rma_status == "pending"

    async with Session() as session:
        with pytest.raises(ValueError, match="already has an RMA"):
            await create_rma(session, RmaCreateInput(return_request_id=rid))

    await engine.dispose()


@pytest.mark.asyncio
async def test_create_rma_missing_row() -> None:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    Session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with Session() as session:
        with pytest.raises(ValueError, match="not found"):
            await create_rma(session, RmaCreateInput(return_request_id="missing"))
    await engine.dispose()
