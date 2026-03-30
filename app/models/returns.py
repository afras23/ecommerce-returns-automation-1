"""
SQLAlchemy models for return records.
"""

import uuid
from datetime import UTC, datetime

from sqlalchemy import Boolean, DateTime, Float, String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class ReturnRecord(Base):
    __tablename__ = "returns"

    id: Mapped[str] = mapped_column(
        String,
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )
    order_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    customer_email: Mapped[str | None] = mapped_column(String, nullable=True)

    reason: Mapped[str] = mapped_column(String, nullable=False)
    preference: Mapped[str] = mapped_column(String, nullable=False)
    purchase_date: Mapped[str] = mapped_column(String, nullable=False)
    order_amount: Mapped[float | None] = mapped_column(Float, nullable=True)
    damaged: Mapped[bool] = mapped_column(Boolean, default=False)
    product_type: Mapped[str | None] = mapped_column(String, nullable=True)

    classification_category: Mapped[str | None] = mapped_column(String, nullable=True)
    classification_confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    risk_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    decision: Mapped[str | None] = mapped_column(String, nullable=True)
    decision_reason: Mapped[str | None] = mapped_column(String, nullable=True)
    routing_outcome: Mapped[str | None] = mapped_column(String, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )
