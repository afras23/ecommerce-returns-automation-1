"""
DB layer: a failed commit surfaces as SQLAlchemyError (callers must handle / translate).
"""

import pytest
from app.models.returns import Base, ReturnRecord
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool


@pytest.mark.asyncio
async def test_async_session_commit_failure_surfaces() -> None:
    engine = create_async_engine(
        "sqlite+aiosqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    Session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with Session() as session:
        session.add(
            ReturnRecord(
                order_id="X",
                reason="r",
                preference="refund",
                purchase_date="2026-03-01",
            )
        )

        async def boom() -> None:
            raise SQLAlchemyError("simulated commit failure")

        session.commit = boom  # type: ignore[method-assign]

        with pytest.raises(SQLAlchemyError, match="simulated commit failure"):
            await session.commit()

    await engine.dispose()
