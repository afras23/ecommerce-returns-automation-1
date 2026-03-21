"""
Unit tests for the scoring service.

Tests verify composite score values, factor boundaries, and that the scoring
model produces outcomes consistent with the decision thresholds in config.
"""

import pytest

from app.config import settings
from app.models.returns import ReturnRecord
from app.services.classification import ClassificationResult
from app.services.scoring import ScoreResult, _WEIGHTS, score
from app.services.validation import ValidationResult


def _record(**kwargs) -> ReturnRecord:
    defaults = {
        "id": "test",
        "order_id": "ORD-001",
        "reason": "some reason",
        "preference": "refund",
        "purchase_date": "2026-03-01",
        "order_amount": 49.99,
        "damaged": False,
    }
    return ReturnRecord(**{**defaults, **kwargs})


def _valid() -> ValidationResult:
    return ValidationResult(valid=True, reasons=[])


def _invalid() -> ValidationResult:
    return ValidationResult(valid=False, reasons=["outside_return_window:400_days"])


def _cls(category: str, confidence: float) -> ClassificationResult:
    return ClassificationResult(category=category, confidence=confidence)


# ---------------------------------------------------------------------------
# Invalid validation short-circuits to zero score
# ---------------------------------------------------------------------------


def test_invalid_validation_yields_zero_score() -> None:
    result = score(_record(), _invalid(), _cls("other", 0.30))
    assert result.score == 0.0
    assert result.classification_factor == 0.0
    assert result.value_factor == 0.0


# ---------------------------------------------------------------------------
# Category clarity drives score below/above approval threshold
# ---------------------------------------------------------------------------


def test_damaged_item_scores_below_approve_threshold() -> None:
    """Damaged items should go to manual review, not auto-approve."""
    result = score(_record(order_amount=49.99), _valid(), _cls("damaged", 0.95))
    assert result.score < settings.auto_approve_score


def test_wrong_item_scores_below_approve_threshold() -> None:
    result = score(_record(order_amount=49.99), _valid(), _cls("wrong_item", 0.95))
    assert result.score < settings.auto_approve_score


def test_buyer_remorse_scores_above_approve_threshold() -> None:
    """Standard buyer-remorse returns should be auto-approvable."""
    result = score(_record(order_amount=49.99), _valid(), _cls("buyer_remorse", 0.85))
    assert result.score >= settings.auto_approve_score


def test_sizing_scores_above_approve_threshold() -> None:
    result = score(_record(order_amount=49.99), _valid(), _cls("sizing", 0.85))
    assert result.score >= settings.auto_approve_score


def test_other_category_scores_below_approve_threshold() -> None:
    """Vague/unknown reasons should require manual review."""
    result = score(_record(order_amount=49.99), _valid(), _cls("other", 0.30))
    assert result.score < settings.auto_approve_score


# ---------------------------------------------------------------------------
# Value factor behaviour
# ---------------------------------------------------------------------------


def test_high_value_order_reduces_score() -> None:
    base = score(_record(order_amount=49.99), _valid(), _cls("buyer_remorse", 0.85))
    high = score(_record(order_amount=999.99), _valid(), _cls("buyer_remorse", 0.85))
    assert high.score < base.score


def test_order_amount_none_treated_as_low_value() -> None:
    with_amount = score(_record(order_amount=49.99), _valid(), _cls("buyer_remorse", 0.85))
    without = score(_record(order_amount=None), _valid(), _cls("buyer_remorse", 0.85))
    # Both should have value_factor = 1.0 → same score
    assert with_amount.score == without.score


def test_medium_value_order_has_intermediate_value_factor() -> None:
    result = score(_record(order_amount=300.0), _valid(), _cls("buyer_remorse", 0.85))
    # $300 > 0.5 * $500 = $250 → value_factor = 0.75 (not full 1.0, not minimum 0.5)
    assert result.value_factor == pytest.approx(0.75)


# ---------------------------------------------------------------------------
# Score invariants
# ---------------------------------------------------------------------------


def test_composite_score_is_within_unit_range() -> None:
    result = score(_record(), _valid(), _cls("buyer_remorse", 1.0))
    assert 0.0 <= result.score <= 1.0


def test_all_factors_are_within_unit_range() -> None:
    result = score(_record(), _valid(), _cls("sizing", 0.90))
    for factor_value in (
        result.classification_factor,
        result.value_factor,
        result.clarity_factor,
        result.history_factor,
    ):
        assert 0.0 <= factor_value <= 1.0


def test_weights_sum_to_one() -> None:
    assert sum(_WEIGHTS.values()) == pytest.approx(1.0)


def test_score_result_type() -> None:
    result = score(_record(), _valid(), _cls("buyer_remorse", 0.85))
    assert isinstance(result, ScoreResult)
    assert isinstance(result.score, float)


# ---------------------------------------------------------------------------
# Higher classification confidence → higher score (within same category)
# ---------------------------------------------------------------------------


def test_higher_classification_confidence_increases_score() -> None:
    low = score(_record(), _valid(), _cls("buyer_remorse", 0.50))
    high = score(_record(), _valid(), _cls("buyer_remorse", 0.95))
    assert high.score > low.score
