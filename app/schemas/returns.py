from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class ReturnRequest(BaseModel):
    order_id: str
    customer_email: Optional[str] = None
    reason: str
    preference: str = Field(pattern="^(refund|exchange)$")
    purchase_date: str  # ISO format: YYYY-MM-DD
    order_amount: Optional[float] = None
    damaged: bool = False
    product_type: Optional[str] = None


class ReturnResponse(BaseModel):
    id: str
    order_id: str
    decision: str
    decision_reason: str
    routing_outcome: str
    classification_category: Optional[str]
    classification_confidence: Optional[float]
    risk_score: Optional[float]
    created_at: datetime

    model_config = {"from_attributes": True}


class ReturnDetail(ReturnResponse):
    customer_email: Optional[str]
    reason: str
    preference: str
    purchase_date: str
    order_amount: Optional[float]
    damaged: bool
    product_type: Optional[str]
    updated_at: datetime
