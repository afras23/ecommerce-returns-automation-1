"""
Unit tests for the decision service.

Tests verify all three decision paths (approved/rejected/manual_review)
and the boundary conditions between them.
"""

import pytest

from app.config import settings
from app.models.returns import ReturnRecord
from app.services.decision import DecisionResult, decide
from app.services.scoring import ScoreResult
from app.services.validation import ValidationResult


def _record(**kwargs) -> ReturnRecord:
    defaults = {
        "id": "test",
        "order_id": "ORD-001",
        "reason": "changed my mind",
        "preference": "refund",
        "purchase_date": "2026-03-01",
        "order_amount": 49.99,
        "damaged": False,
    }
    return ReturnRecord(**{**defaults, **kwargs})


def _valid() -> ValidationResult:
    return ValidationResult(valid=True, reasons=[])


def _invalid(*reasons: str) -> ValidationResult:
    return ValidationResult(valid=False, reasons=list(reasons))


def _score(value: float) -> ScoreResult:
    return ScoreResult(
        score=value,
        classification_factor=value,
        value_factor=1.0,
        clarity_factor=value,
        history_factor=1.0,
    )


# ---------------------------------------------------------------------------
# Hard rule 1: validation failure → always reject
# ---------------------------------------------------------------------------


def test_invalid_validation_always_rejects_even_with_perfect_score() -> None:
    result = decide(_record(), _invalid("outside_return_window:400_days"), _score(1.0))
    assert result.decision == "rejected"


def test_rejected_reason_contains_validation_codes() -> None:
    result = decide(
        _record(),
        _invalid("outside_return_window:400_days", "restricted_product_type:digital"),
        _score(0.0),
    )
    assert result.decision == "rejected"
    assert "outside_return_window" in result.reason
    assert "restricted_product_type" in result.reason


def test_multiple_validation_failures_are_all_in_reason() -> None:
    result = decide(
        _record(),
        _invalid("reason_a", "reason_b", "reason_c"),
        _score(0.0),
    )
    assert "reason_a" in result.reason
    assert "reason_b" in result.reason
    assert "reason_c" in result.reason


# ---------------------------------------------------------------------------
# Hard rule 2: high-value order → always manual_review
# ---------------------------------------------------------------------------


def test_high_value_order_forces_manual_review_even_with_high_score() -> None:
    record = _record(order_amount=settings.refund_threshold_amount + 1)
    result = decide(record, _valid(), _score(1.0))
    assert result.decision == "manual_review"
    assert result.reason == "high_value_order"


def test_order_just_below_threshold_is_not_escalated() -> None:
    record = _record(order_amount=settings.refund_threshold_amount - 0.01)
    result = decide(record, _valid(), _score(1.0))
    assert result.decision == "approved"


def test_high_value_rule_respects_config_flag(monkeypatch) -> None:
    """Disabling high_value_manual_review lets high-value orders score-through."""
    monkeypatch.setattr(settings, "high_value_manual_review", False)
    record = _record(order_amount=999.99)
    result = decide(record, _valid(), _score(1.0))
    assert result.decision == "approved"


# ---------------------------------------------------------------------------
# Score-based gate
# ---------------------------------------------------------------------------


def test_score_at_threshold_approves() -> None:
    result = decide(_record(), _valid(), _score(settings.auto_approve_score))
    assert result.decision == "approved"


def test_score_above_threshold_approves() -> None:
    result = decide(_record(), _valid(), _score(settings.auto_approve_score + 0.1))
    assert result.decision == "approved"


def test_score_just_below_threshold_sends_to_manual_review() -> None:
    result = decide(_record(), _valid(), _score(settings.auto_approve_score - 0.001))
    assert result.decision == "manual_review"


def test_score_of_zero_sends_to_manual_review_when_valid() -> None:
    """A valid return (passed policy) with score 0 should still get human eyes."""
    result = decide(_record(), _valid(), _score(0.0))
    assert result.decision == "manual_review"


# ---------------------------------------------------------------------------
# Reason codes
# ---------------------------------------------------------------------------


def test_approved_reason_contains_score() -> None:
    s = 0.85
    result = decide(_record(), _valid(), _score(s))
    assert result.decision == "approved"
    assert "score:" in result.reason


def test_manual_review_low_confidence_reason_contains_score() -> None:
    s = 0.50
    result = decide(_record(), _valid(), _score(s))
    assert result.decision == "manual_review"
    assert "low_confidence_score:" in result.reason


def test_return_type_is_decision_result() -> None:
    result = decide(_record(), _valid(), _score(0.85))
    assert isinstance(result, DecisionResult)
    assert isinstance(result.decision, str)
    assert isinstance(result.reason, str)
