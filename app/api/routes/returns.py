"""
Return request HTTP API.
"""

from fastapi import APIRouter, HTTPException
from sqlalchemy import select

from app import database
from app.api.schemas.returns import ReturnDetail, ReturnRequest, ReturnResponse
from app.core.metrics import metrics
from app.models.returns import ReturnRecord
from app.services import audit, ingestion
from app.services.orchestrator import process_return

router = APIRouter(prefix="/api/v1", tags=["returns"])


@router.post("/returns", response_model=ReturnResponse, status_code=201)
async def create_return(data: ReturnRequest) -> ReturnRecord:
    record = ingestion.ingest(data)
    pipeline = process_return(record)

    record.classification_category = pipeline.classification.category
    record.classification_confidence = pipeline.classification.confidence
    record.risk_score = pipeline.score.score
    record.decision = pipeline.decision.decision
    record.decision_reason = pipeline.decision.reason
    record.routing_outcome = pipeline.routing_outcome

    audit.log_pipeline(record, pipeline)
    metrics.record(pipeline.decision.decision)

    async with database.async_session() as session:
        session.add(record)
        await session.commit()
        await session.refresh(record)

    return record


@router.get("/returns/{return_id}", response_model=ReturnDetail)
async def get_return(return_id: str) -> ReturnRecord:
    async with database.async_session() as session:
        result = await session.execute(
            select(ReturnRecord).where(ReturnRecord.id == return_id)
        )
        record = result.scalar_one_or_none()

    if record is None:
        raise HTTPException(status_code=404, detail="Return not found")

    return record
