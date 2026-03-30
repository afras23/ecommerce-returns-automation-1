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
    product_id: str | None = None
    customer_segment: str | None = None


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
    product_id: str | None = None
    customer_segment: str | None = None
    fraud_score: float | None = None
    processing_time_ms: float | None = None
    shipping_label_json: str | None = None
    updated_at: datetime


class ProcessReturnResponse(ReturnDetail):
    """Extended response for process endpoints with request tracing."""

    correlation_id: str | None = None


class BatchReturnRequest(BaseModel):
    """Batch of return requests processed in order."""

    items: list[ReturnRequest] = Field(min_length=1, max_length=50)


class BatchReturnResponse(BaseModel):
    results: list[ProcessReturnResponse]
    correlation_id: str | None = None
