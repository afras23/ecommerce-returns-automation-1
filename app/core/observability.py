"""
Structured logging helpers for pipeline stages (correlation-aware).
"""

import logging

from app.core.context import correlation_id_ctx

logger = logging.getLogger(__name__)


def log_classification_event(
    *,
    category: str,
    confidence: float,
    return_id: str | None = None,
) -> None:
    logger.info(
        "classification",
        extra={
            "correlation_id": correlation_id_ctx.get(),
            "return_id": return_id,
            "classification_category": category,
            "classification_confidence": confidence,
        },
    )


def log_fraud_event(
    *,
    fraud_score: float,
    risk_level: str,
    flags: tuple[str, ...],
    customer_key: str,
    return_id: str | None = None,
) -> None:
    logger.info(
        "fraud_scoring",
        extra={
            "correlation_id": correlation_id_ctx.get(),
            "return_id": return_id,
            "customer_key": customer_key,
            "fraud_score": fraud_score,
            "risk_level": risk_level,
            "fraud_flags": list(flags),
        },
    )


def log_refund_event(
    *,
    refund_amount: float,
    percentage: float,
    fees: float,
    condition: str,
    return_id: str | None = None,
) -> None:
    logger.info(
        "refund_calculation",
        extra={
            "correlation_id": correlation_id_ctx.get(),
            "return_id": return_id,
            "refund_amount": refund_amount,
            "refund_percentage": percentage,
            "fees": fees,
            "condition": condition,
        },
    )
