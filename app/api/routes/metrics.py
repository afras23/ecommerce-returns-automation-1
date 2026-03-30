"""
Application metrics snapshot (in-process counters).
"""

from fastapi import APIRouter

from app.config import settings
from app.core.metrics import metrics

router = APIRouter(tags=["observability"])


@router.get("/metrics")
async def get_metrics() -> dict:
    """Return decision pipeline counters and rates."""
    if not settings.metrics_enabled:
        return {"enabled": False}
    return metrics.snapshot()
