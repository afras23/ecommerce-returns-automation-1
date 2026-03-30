"""
Analytics service interface: aggregates and exports decision metrics.

Complements in-process counters in ``app.core.metrics`` for BI pipelines.
"""

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class AnalyticsSummaryInput:
    """Time window or filter for aggregation."""

    window_hours: int


@dataclass(frozen=True)
class AnalyticsSummaryOutput:
    """Rollup counts for reporting."""

    total_returns: int
    approved: int
    rejected: int
    manual_review: int


class AnalyticsService(Protocol):
    """
    Computes analytics summaries for operations and product review.

    Expected behavior:
        - Use the same decision labels as the core pipeline.
        - Be safe to call from batch jobs (no request-scoped state required).
    """

    def summary(self, data: AnalyticsSummaryInput) -> AnalyticsSummaryOutput:
        ...
