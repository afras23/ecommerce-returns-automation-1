"""
Async orchestration: legacy pipeline + fraud scoring + observability logging.
"""

from __future__ import annotations

import logging
import time
from datetime import UTC

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.schemas.returns import ReturnRequest
from app.config import Settings
from app.core.context import correlation_id_ctx
from app.core.metrics import metrics as decision_metrics
from app.core.metrics import observability_metrics
from app.core.observability import (
    log_classification_event,
    log_fraud_event,
    log_refund_event,
)
from app.models.returns import ReturnRecord
from app.services import audit, ingestion
from app.services.fraud_service import (
    FraudAssessmentInput,
    ReturnHistoryEntry,
    assess_fraud,
)
from app.services.orchestrator import PipelineResult, process_return
from app.services.product_condition_service import ProductCondition
from app.services.refund_service import RefundComputationInput, compute_refund

logger = logging.getLogger(__name__)


async def _history_for_customer(
    session: AsyncSession,
    *,
    customer_email: str | None,
    exclude_return_id: str,
) -> tuple[ReturnHistoryEntry, ...]:
    if not customer_email:
        return ()
    result = await session.execute(
        select(ReturnRecord)
        .where(ReturnRecord.customer_email == customer_email)
        .where(ReturnRecord.id != exclude_return_id)
        .order_by(ReturnRecord.created_at.desc())
        .limit(50)
    )
    rows = result.scalars().all()
    entries: list[ReturnHistoryEntry] = []
    for row in rows:
        entries.append(
            ReturnHistoryEntry(
                return_id=row.id,
                order_amount=float(row.order_amount or 0.0),
                created_at=row.created_at.replace(tzinfo=UTC)
                if row.created_at.tzinfo is None
                else row.created_at.astimezone(UTC),
            )
        )
    return tuple(entries)


def _apply_pipeline_to_record(record: ReturnRecord, pipeline: PipelineResult) -> None:
    record.classification_category = pipeline.classification.category
    record.classification_confidence = pipeline.classification.confidence
    record.risk_score = pipeline.score.score
    record.decision = pipeline.decision.decision
    record.decision_reason = pipeline.decision.reason
    record.routing_outcome = pipeline.routing_outcome


async def run_return_pipeline(
    session: AsyncSession,
    data: ReturnRequest,
    *,
    settings: Settings,
) -> tuple[ReturnRecord, PipelineResult, float, float]:
    """
    Ingest, run sync pipeline, score fraud from DB history, attach timings and logs.

    Returns:
        record, pipeline, fraud_score, processing_time_ms
    """
    record = ingestion.ingest(data)
    t0 = time.perf_counter()
    pipeline = process_return(record)
    _apply_pipeline_to_record(record, pipeline)

    history = await _history_for_customer(
        session,
        customer_email=record.customer_email,
        exclude_return_id=record.id,
    )
    cust_key = record.customer_email or "anonymous"
    fraud_out = assess_fraud(
        FraudAssessmentInput(
            customer_id=cust_key,
            return_history=history,
        ),
        settings=settings,
    )
    record.fraud_score = fraud_out.fraud_score

    processing_ms = (time.perf_counter() - t0) * 1000.0
    record.processing_time_ms = round(processing_ms, 3)

    cid = correlation_id_ctx.get()
    log_classification_event(
        category=pipeline.classification.category,
        confidence=pipeline.classification.confidence,
        return_id=record.id,
    )
    log_fraud_event(
        fraud_score=fraud_out.fraud_score,
        risk_level=fraud_out.risk_level,
        flags=fraud_out.flags,
        customer_key=cust_key,
        return_id=record.id,
    )
    logger.info(
        "pipeline_decision",
        extra={
            "correlation_id": cid,
            "return_id": record.id,
            "decision": pipeline.decision.decision,
            "routing_outcome": pipeline.routing_outcome,
            "processing_time_ms": record.processing_time_ms,
        },
    )

    if record.order_amount is not None:
        ref = compute_refund(
            RefundComputationInput(
                order_amount=record.order_amount,
                condition=ProductCondition.OPENED_UNUSED,
            ),
            settings=settings,
        )
        log_refund_event(
            refund_amount=ref.refund_amount,
            percentage=ref.percentage,
            fees=ref.fees,
            condition=ProductCondition.OPENED_UNUSED.value,
            return_id=record.id,
        )

    audit.log_pipeline(record, pipeline)
    decision_metrics.record(pipeline.decision.decision)
    observability_metrics.record_processing(
        processing_time_ms=processing_ms,
        fraud_score=fraud_out.fraud_score,
        fraud_flag_threshold=settings.fraud_flagged_processing_threshold,
    )

    return record, pipeline, fraud_out.fraud_score, processing_ms
