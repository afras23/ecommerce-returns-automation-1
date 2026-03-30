"""
Pydantic models for return API requests and responses.
"""

from datetime import datetime

from pydantic import BaseModel, Field


class ReturnRequest(BaseModel):
    order_id: str
    customer_email: str | None = None
    reason: str
    preference: str = Field(pattern="^(refund|exchange)$")
    purchase_date: str
    order_amount: float | None = None
    damaged: bool = False
    product_type: str | None = None


class ReturnResponse(BaseModel):
    id: str
    order_id: str
    decision: str
    decision_reason: str
    routing_outcome: str
    classification_category: str | None
    classification_confidence: float | None
    risk_score: float | None
    created_at: datetime

    model_config = {"from_attributes": True}


class ReturnDetail(ReturnResponse):
    customer_email: str | None
    reason: str
    preference: str
    purchase_date: str
    order_amount: float | None
    damaged: bool
    product_type: str | None
    updated_at: datetime
