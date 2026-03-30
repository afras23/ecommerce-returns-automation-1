"""
Parameterized classification and fraud scoring (deterministic, no I/O).
"""

from datetime import UTC, datetime, timedelta

import pytest
from app.config import Settings
from app.models.returns import ReturnRecord
from app.services.classification import classify
from app.services.fraud_service import (
    FraudAssessmentInput,
    ReturnHistoryEntry,
    assess_fraud,
)


@pytest.mark.parametrize(
    ("reason", "expected_category"),
    [
        ("changed my mind about this purchase", "buyer_remorse"),
        ("you sent the wrong item completely", "wrong_item"),
        ("package arrived damaged and cracked", "damaged"),
        ("not as described on the website", "not_as_described"),
        ("wrong size — too small", "sizing"),
        ("   ", "other"),
        ("", "other"),
        ("something vague xyzabc", "other"),
    ],
)
def test_classify_reason_categories(reason: str, expected_category: str) -> None:
    record = ReturnRecord(
        order_id="O1",
        reason=reason,
        preference="refund",
        purchase_date="2026-03-01",
        damaged=False,
    )
    out = classify(record)
    assert out.category == expected_category


@pytest.mark.parametrize("damaged", [True, False])
def test_damaged_flag_overrides_text_category(damaged: bool) -> None:
    record = ReturnRecord(
        order_id="O1",
        reason="changed my mind",
        preference="refund",
        purchase_date="2026-03-01",
        damaged=damaged,
    )
    out = classify(record)
    if damaged:
        assert out.category == "damaged"
    else:
        assert out.category == "buyer_remorse"


@pytest.mark.parametrize(
    ("entries", "expected_risk"),
    [
        ([], "low"),
        (
            [
                ReturnHistoryEntry(
                    return_id="a",
                    order_amount=50.0,
                    created_at=datetime(2026, 3, 15, 12, 0, tzinfo=UTC),
                )
            ],
            "low",
        ),
    ],
)
def test_fraud_risk_by_history_size(
    entries: list[ReturnHistoryEntry],
    expected_risk: str,
) -> None:
    settings = Settings()
    now = datetime(2026, 3, 20, 12, 0, tzinfo=UTC)
    out = assess_fraud(
        FraudAssessmentInput(customer_id="cust-1", return_history=tuple(entries)),
        settings=settings,
        now=now,
    )
    assert out.risk_level == expected_risk


def test_fraud_high_frequency_flags_high_risk() -> None:
    """Five returns in-window should trigger high_return_frequency and elevated score."""
    settings = Settings(fraud_frequency_high_count=5)
    now = datetime(2026, 3, 20, 12, 0, tzinfo=UTC)
    entries = [
        ReturnHistoryEntry(
            return_id=f"r{i}",
            order_amount=200.0,
            created_at=now - timedelta(days=i),
        )
        for i in range(5)
    ]
    out = assess_fraud(
        FraudAssessmentInput(customer_id="heavy-user", return_history=tuple(entries)),
        settings=settings,
        now=now,
    )
    assert "high_return_frequency" in out.flags
    assert out.risk_level in ("medium", "high")


def test_fraud_aggregate_value_flag() -> None:
    settings = Settings(fraud_total_value_high_usd=1000.0)
    now = datetime(2026, 3, 20, 12, 0, tzinfo=UTC)
    entries = [
        ReturnHistoryEntry(
            return_id="r1",
            order_amount=2000.0,
            created_at=now - timedelta(days=1),
        )
    ]
    out = assess_fraud(
        FraudAssessmentInput(customer_id="big-spender", return_history=tuple(entries)),
        settings=settings,
        now=now,
    )
    assert "high_aggregate_value" in out.flags
