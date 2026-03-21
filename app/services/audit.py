"""
Audit: structured logging of every return decision for compliance and debugging.
Each log entry is self-contained — no joins required to reconstruct a decision.
"""

from app.core.logging import get_logger
from app.models.returns import ReturnRecord

_logger = get_logger("audit")


def log_decision(record: ReturnRecord) -> None:
    _logger.info(
        "return_decision",
        extra={
            "return_id": record.id,
            "order_id": record.order_id,
            "decision": record.decision,
            "reason": record.decision_reason,
            "outcome": record.routing_outcome,
            "purchase_date": record.purchase_date,
            "damaged": record.damaged,
            "order_amount": record.order_amount,
            "preference": record.preference,
            "product_type": record.product_type,
        },
    )
