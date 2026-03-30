"""
Application metrics snapshot (in-process counters).
"""

from fastapi import APIRouter

from app.config import settings
from app.core.metrics import combined_metrics_snapshot

router = APIRouter(tags=["observability"])


@router.get("/metrics")
async def get_metrics() -> dict:
    """Return decision pipeline counters, fraud flagging, and latency averages."""
    if not settings.metrics_enabled:
        return {"enabled": False}
    return combined_metrics_snapshot()
