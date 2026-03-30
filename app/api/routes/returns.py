"""
Return request HTTP API (process, batch, single resource).
"""

from fastapi import APIRouter, HTTPException, Query, Request
from sqlalchemy import select

from app import database
from app.api.schemas.returns import (
    BatchReturnRequest,
    BatchReturnResponse,
    ProcessReturnResponse,
    ReturnDetail,
    ReturnRequest,
    ReturnResponse,
)
from app.config import settings
from app.core.context import correlation_id_ctx
from app.integrations.shipping_client import attach_label_to_return
from app.models.returns import ReturnRecord
from app.services.process_return_service import run_return_pipeline

router = APIRouter(prefix="/api/v1", tags=["returns"])


def _correlation_id(request: Request) -> str | None:
    return getattr(request.state, "request_id", None) or correlation_id_ctx.get()


@router.post("/returns", response_model=ReturnResponse, status_code=201)
async def create_return(request: Request, data: ReturnRequest) -> ReturnRecord:
    """Create and process a return (legacy path; same engine as /returns/process)."""
    async with database.async_session() as session:
        record, _, _, _ = await run_return_pipeline(session, data, settings=settings)
        session.add(record)
        await session.commit()
        await session.refresh(record)
    return record


@router.post("/returns/process", response_model=ProcessReturnResponse, status_code=201)
async def process_return_endpoint(
    request: Request,
    data: ReturnRequest,
    attach_shipping: bool = Query(
        False,
        description="Generate mock label and attach to return row",
    ),
) -> ProcessReturnResponse:
    """Process a return with fraud scoring, observability logging, and optional shipping label."""
    async with database.async_session() as session:
        record, _, _, _ = await run_return_pipeline(session, data, settings=settings)
        session.add(record)
        await session.flush()
        if attach_shipping:
            await attach_label_to_return(session, return_id=record.id)
        await session.commit()
        await session.refresh(record)
    base = ProcessReturnResponse.model_validate(record, from_attributes=True)
    return base.model_copy(update={"correlation_id": _correlation_id(request)})


@router.post("/returns/batch", response_model=BatchReturnResponse, status_code=201)
async def batch_process_returns(request: Request, body: BatchReturnRequest) -> BatchReturnResponse:
    """Process up to 50 returns sequentially within the same correlation scope."""
    results: list[ProcessReturnResponse] = []
    async with database.async_session() as session:
        for item in body.items:
            record, _, _, _ = await run_return_pipeline(session, item, settings=settings)
            session.add(record)
            await session.flush()
            await session.refresh(record)
            pr = ProcessReturnResponse.model_validate(record, from_attributes=True)
            results.append(pr.model_copy(update={"correlation_id": _correlation_id(request)}))
        await session.commit()
    return BatchReturnResponse(
        results=results,
        correlation_id=_correlation_id(request),
    )


@router.get("/returns/{return_id}", response_model=ReturnDetail)
async def get_return(return_id: str) -> ReturnRecord:
    async with database.async_session() as session:
        result = await session.execute(
            select(ReturnRecord).where(ReturnRecord.id == return_id),
        )
        record = result.scalar_one_or_none()

    if record is None:
        raise HTTPException(status_code=404, detail="Return not found")

    return record
