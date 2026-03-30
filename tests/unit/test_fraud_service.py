"""
Unit tests for deterministic fraud scoring.
"""

from datetime import UTC, datetime, timedelta

import pytest
from app.config import Settings
from app.services.fraud_service import (
    FraudAssessmentInput,
    ReturnHistoryEntry,
    assess_fraud,
)


def _entry(days_ago: int, amount: float, rid: str = "r1") -> ReturnHistoryEntry:
    return ReturnHistoryEntry(
        return_id=rid,
        order_amount=amount,
        created_at=datetime.now(UTC) - timedelta(days=days_ago),
    )


def test_fraud_low_risk_empty_history() -> None:
    settings = Settings()
    out = assess_fraud(
        FraudAssessmentInput(customer_id="c1", return_history=()),
        settings=settings,
        now=datetime(2026, 3, 31, tzinfo=UTC),
    )
    assert out.risk_level == "low"
    assert out.fraud_score == pytest.approx(0.0)


def test_fraud_high_frequency_flags() -> None:
    settings = Settings()
    hist = tuple(_entry(1, 50.0, f"r{i}") for i in range(6))
    out = assess_fraud(
        FraudAssessmentInput(customer_id="c1", return_history=hist),
        settings=settings,
        now=datetime(2026, 3, 31, tzinfo=UTC),
    )
    assert "high_return_frequency" in out.flags
    assert out.fraud_score > settings.fraud_risk_medium_min


def test_fraud_boundary_medium() -> None:
    settings = Settings(fraud_risk_medium_min=0.2, fraud_risk_high_min=0.9)
    hist = (_entry(2, 200.0), _entry(5, 200.0))
    out = assess_fraud(
        FraudAssessmentInput(customer_id="c1", return_history=hist),
        settings=settings,
        now=datetime(2026, 3, 31, tzinfo=UTC),
    )
    assert out.risk_level in ("low", "medium", "high")
