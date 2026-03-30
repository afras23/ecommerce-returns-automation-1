import app.database as db_module
import pytest
import pytest_asyncio
from app.core.metrics import metrics
from app.models.returns import Base
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine


@pytest_asyncio.fixture(autouse=True)
async def isolated_db():
    """Spin up a fresh in-memory SQLite DB for every test."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Patch module-level references used by routes
    original_engine = db_module.engine
    original_session = db_module.async_session

    db_module.engine = engine
    db_module.async_session = async_sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )

    yield

    db_module.engine = original_engine
    db_module.async_session = original_session
    await engine.dispose()


@pytest.fixture(autouse=True)
def reset_metrics():
    """Ensure metrics counters don't bleed between tests."""
    metrics.reset()
    yield
    metrics.reset()
