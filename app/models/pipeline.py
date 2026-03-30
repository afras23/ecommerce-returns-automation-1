"""
Pipeline persistence models: customers, return requests, history, audit trail.

Co-located to avoid circular SQLAlchemy relationship imports.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import DateTime, Float, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.returns import Base


class Customer(Base):
    __tablename__ = "customers"

    id: Mapped[str] = mapped_column(
        String,
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )
    external_customer_id: Mapped[str] = mapped_column(String, unique=True, index=True)
    email: Mapped[str | None] = mapped_column(String, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )

    return_requests: Mapped[list[ReturnRequest]] = relationship(
        back_populates="customer",
        cascade="all, delete-orphan",
    )
    history_entries: Mapped[list[ReturnHistory]] = relationship(
        back_populates="customer",
        cascade="all, delete-orphan",
    )


class ReturnRequest(Base):
    """
    Canonical return request for the pipeline (classification, RMA, refunds).

    Distinct from legacy ``ReturnRecord`` in ``returns`` used by the public v1 API.
    """

    __tablename__ = "return_requests"

    id: Mapped[str] = mapped_column(
        String,
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )
    customer_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("customers.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    order_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    order_amount: Mapped[float | None] = mapped_column(Float, nullable=True)
    status: Mapped[str] = mapped_column(String, default="pending", index=True)

    rma_id: Mapped[str | None] = mapped_column(String, unique=True, nullable=True, index=True)
    rma_status: Mapped[str | None] = mapped_column(String, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )

    customer: Mapped[Customer] = relationship(back_populates="return_requests")
    history_entries: Mapped[list[ReturnHistory]] = relationship(
        back_populates="return_request",
        cascade="all, delete-orphan",
    )


class ReturnHistory(Base):
    """Historical return events per customer (inputs for fraud scoring)."""

    __tablename__ = "return_history"

    id: Mapped[str] = mapped_column(
        String,
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )
    customer_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("customers.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    return_request_id: Mapped[str | None] = mapped_column(
        String,
        ForeignKey("return_requests.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    order_amount: Mapped[float] = mapped_column(Float, default=0.0)
    recorded_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC))

    customer: Mapped[Customer] = relationship(back_populates="history_entries")
    return_request: Mapped[ReturnRequest | None] = relationship(
        back_populates="history_entries",
    )


class AuditLog(Base):
    """Append-only audit events for compliance and debugging."""

    __tablename__ = "audit_logs"

    id: Mapped[str] = mapped_column(
        String,
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )
    entity_type: Mapped[str] = mapped_column(String, nullable=False, index=True)
    entity_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    action: Mapped[str] = mapped_column(String, nullable=False)
    payload_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC))
