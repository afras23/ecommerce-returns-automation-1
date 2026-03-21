from fastapi import APIRouter, HTTPException
from sqlalchemy import select

from app import database
from app.core.metrics import metrics
from app.models.returns import ReturnRecord
from app.schemas.returns import ReturnDetail, ReturnRequest, ReturnResponse
from app.services import audit, classification, decision, ingestion, routing, validation

router = APIRouter(prefix="/api/v1", tags=["returns"])


@router.post("/returns", response_model=ReturnResponse, status_code=201)
async def create_return(data: ReturnRequest) -> ReturnRecord:
    record = ingestion.ingest(data)

    val_result = validation.validate(record)
    classification_result = classification.classify(record)
    decision_result = decision.decide(record, val_result, classification_result)
    routing_outcome = routing.route(record, decision_result)

    record.decision = decision_result.decision
    record.decision_reason = decision_result.reason
    record.routing_outcome = routing_outcome

    audit.log_decision(record)
    metrics.record(decision_result.decision)

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
