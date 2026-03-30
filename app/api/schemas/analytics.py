"""
Response models for analytics endpoints.
"""

from typing import Any

from pydantic import BaseModel, Field


class AnalyticsPage(BaseModel):
    """Paginated bucketed rates (share of filtered population)."""

    rows: list[dict[str, Any]] = Field(description="Each row: bucket, count, rate")
    total_returns: int
    page: int
    page_size: int
