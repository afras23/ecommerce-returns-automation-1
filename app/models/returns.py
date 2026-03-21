import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, Column, DateTime, Float, String
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


class ReturnRecord(Base):
    __tablename__ = "returns"

    # Identity
    id: str = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    order_id: str = Column(String, nullable=False, index=True)
    customer_email: str = Column(String, nullable=True)

    # Request fields
    reason: str = Column(String, nullable=False)
    preference: str = Column(String, nullable=False)  # refund | exchange
    purchase_date: str = Column(String, nullable=False)
    order_amount: float = Column(Float, nullable=True)
    damaged: bool = Column(Boolean, default=False)
    product_type: str = Column(String, nullable=True)

    # Pipeline outputs (populated after processing)
    classification_category: str = Column(String, nullable=True)
    classification_confidence: float = Column(Float, nullable=True)
    risk_score: float = Column(Float, nullable=True)
    decision: str = Column(String, nullable=True)        # approved | rejected | manual_review
    decision_reason: str = Column(String, nullable=True)
    routing_outcome: str = Column(String, nullable=True)

    # Timestamps
    created_at: datetime = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )
