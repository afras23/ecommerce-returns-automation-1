"""
Ingestion: converts a validated API request into a ReturnRecord ready for the pipeline.
No business logic here — just mapping.
"""

import uuid
from datetime import datetime, timezone

from app.models.returns import ReturnRecord
from app.schemas.returns import ReturnRequest


def ingest(data: ReturnRequest) -> ReturnRecord:
    return ReturnRecord(
        id=str(uuid.uuid4()),
        order_id=data.order_id,
        customer_email=data.customer_email,
        reason=data.reason,
        preference=data.preference,
        purchase_date=data.purchase_date,
        order_amount=data.order_amount,
        damaged=data.damaged,
        product_type=data.product_type,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
