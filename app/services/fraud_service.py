"""
Deterministic fraud scoring from customer return history (no AI).

Uses configurable thresholds from ``app.config.settings``.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.config import Settings


@dataclass(frozen=True)
class ReturnHistoryEntry:
    """Single historical return event for fraud feature extraction."""

    return_id: str
    order_amount: float
    created_at: datetime


@dataclass(frozen=True)
class FraudAssessmentInput:
    """Inputs for fraud scoring."""

    customer_id: str
    return_history: tuple[ReturnHistoryEntry, ...]


@dataclass(frozen=True)
class FraudAssessmentOutput:
    """Fraud score, discrete risk level, and human-readable flags."""

    fraud_score: float
    risk_level: str
    flags: tuple[str, ...]


def _ensure_utc(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=UTC)
    return dt.astimezone(UTC)


def assess_fraud(
    data: FraudAssessmentInput,
    *,
    settings: Settings,
    now: datetime | None = None,
) -> FraudAssessmentOutput:
    """
    Compute a reproducible fraud score from return frequency, value, and recency.

    Args:
        data: Customer id and immutable return history snapshot.
        settings: Threshold and weight configuration.
        now: Clock injection for deterministic tests (UTC).

    Returns:
        FraudAssessmentOutput with score in [0,1], risk level, and flags.
    """
    clock = _ensure_utc(now or datetime.now(UTC))
    window_start = clock - timedelta(days=settings.fraud_window_days)

    windowed = [h for h in data.return_history if _ensure_utc(h.created_at) >= window_start]
    frequency = len(windowed)
    total_value = sum(h.order_amount for h in windowed)
    avg_value = (total_value / frequency) if frequency else 0.0

    if windowed:
        most_recent = max(_ensure_utc(h.created_at) for h in windowed)
        recency_days = (clock - most_recent).total_seconds() / 86400.0
    else:
        recency_days = float(settings.fraud_window_days)

    freq_norm = min(1.0, frequency / max(1, settings.fraud_frequency_high_count))
    total_norm = min(1.0, total_value / max(1.0, settings.fraud_total_value_high_usd))
    avg_norm = min(1.0, avg_value / max(1.0, settings.fraud_avg_order_value_high_usd))
    value_norm = (total_norm + avg_norm) / 2.0
    recency_norm = max(
        0.0,
        1.0 - min(1.0, recency_days / max(1, settings.fraud_recency_hot_days)),
    )

    score = (
        settings.fraud_weight_frequency * freq_norm
        + settings.fraud_weight_value * value_norm
        + settings.fraud_weight_recency * recency_norm
    )
    score = round(min(1.0, max(0.0, score)), 4)

    flags: list[str] = []
    if frequency >= settings.fraud_frequency_high_count:
        flags.append("high_return_frequency")
    if total_value >= settings.fraud_total_value_high_usd:
        flags.append("high_aggregate_value")
    if windowed and recency_days <= settings.fraud_recency_hot_days:
        flags.append("very_recent_return")

    if score >= settings.fraud_risk_high_min:
        risk = "high"
    elif score >= settings.fraud_risk_medium_min:
        risk = "medium"
    else:
        risk = "low"

    return FraudAssessmentOutput(
        fraud_score=score,
        risk_level=risk,
        flags=tuple(flags),
    )
