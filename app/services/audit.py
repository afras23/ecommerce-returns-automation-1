"""
Audit: structured logging of the full pipeline state for every return.

Each entry is self-contained — no joins are required to reconstruct
a decision or debug a misclassification after the fact.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from app.core.logging import get_logger
from app.models.returns import ReturnRecord

if TYPE_CHECKING:
    from app.services.orchestrator import PipelineResult

_logger = get_logger("audit")


def log_pipeline(record: ReturnRecord, pipeline: PipelineResult) -> None:
    """
    Emit a structured log entry capturing the full return pipeline state.

    Args:
        record: The return record with decision/routing fields already set.
        pipeline: The PipelineResult from the orchestrator.
    """
    _logger.info(
        "return_decision",
        extra={
            # Identity
            "return_id": record.id,
            "order_id": record.order_id,
            # Final outcome
            "decision": record.decision,
            "decision_reason": record.decision_reason,
            "routing_outcome": record.routing_outcome,
            # Validation
            "validation_valid": pipeline.validation.valid,
            "validation_reasons": pipeline.validation.reasons,
            # Classification
            "classification_category": pipeline.classification.category,
            "classification_confidence": pipeline.classification.confidence,
            # Scoring
            "risk_score": pipeline.score.score,
            "score_factors": {
                "classification": pipeline.score.classification_factor,
                "value": pipeline.score.value_factor,
                "clarity": pipeline.score.clarity_factor,
                "history": pipeline.score.history_factor,
            },
            # Request context
            "purchase_date": record.purchase_date,
            "order_amount": record.order_amount,
            "damaged": record.damaged,
            "preference": record.preference,
            "product_type": record.product_type,
        },
    )
