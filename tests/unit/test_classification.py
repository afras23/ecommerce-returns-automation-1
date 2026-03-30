"""
Unit tests for the classification service.

Tests verify both category assignment and confidence bounds across
all supported categories and boundary conditions.
"""

import pytest
from app.models.returns import ReturnRecord
from app.services.classification import ClassificationResult, classify


def _record(reason: str = "", damaged: bool = False) -> ReturnRecord:
    return ReturnRecord(
        id="test",
        order_id="ORD-001",
        reason=reason,
        preference="refund",
        purchase_date="2026-03-01",
        order_amount=49.99,
        damaged=damaged,
    )


# ---------------------------------------------------------------------------
# Category assignment — parametrised across all categories
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "reason,damaged,expected_category,min_confidence",
    [
        # damaged
        ("Item arrived completely shattered", False, "damaged", 0.90),
        ("The product is defective and broken", False, "damaged", 0.80),
        ("", True, "damaged", 0.90),        # structural flag — no reason needed
        ("Changed my mind", True, "damaged", 0.90),  # flag overrides text
        # wrong_item
        ("This is the wrong item, I ordered a blue one", False, "wrong_item", 0.90),
        ("Received wrong product entirely", False, "wrong_item", 0.90),
        ("Not what I ordered at all", False, "wrong_item", 0.85),
        # not_as_described
        ("Product is not as described on the website", False, "not_as_described", 0.85),
        ("Misleading description — nothing like the photo", False, "not_as_described", 0.80),
        # sizing
        ("Doesn't fit, too small for me", False, "sizing", 0.80),
        ("Wrong size sent — ordered M but got XL", False, "sizing", 0.85),
        ("Too big, won't work for my use case", False, "sizing", 0.80),
        # buyer_remorse
        ("Changed my mind about this purchase", False, "buyer_remorse", 0.80),
        ("No longer need this item", False, "buyer_remorse", 0.80),
        ("Ordered by mistake, please cancel", False, "buyer_remorse", 0.85),
        # other (fallback)
        ("Random text with no recognisable keywords here", False, "other", 0.25),
        ("", False, "other", 0.25),
    ],
)
def test_classify_category_and_confidence(
    reason: str,
    damaged: bool,
    expected_category: str,
    min_confidence: float,
) -> None:
    result = classify(_record(reason=reason, damaged=damaged))
    assert result.category == expected_category, (
        f"Expected {expected_category!r} for reason={reason!r}, damaged={damaged}"
    )
    assert result.confidence >= min_confidence, (
        f"Expected confidence >= {min_confidence}, got {result.confidence}"
    )


# ---------------------------------------------------------------------------
# Confidence range invariant
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "reason",
    [
        "broken",
        "wrong item",
        "doesn't fit",
        "changed my mind",
        "not as described",
        "completely unrelated text",
        "",
    ],
)
def test_confidence_is_always_between_0_and_1(reason: str) -> None:
    result = classify(_record(reason=reason))
    assert 0.0 <= result.confidence <= 1.0


# ---------------------------------------------------------------------------
# Return type
# ---------------------------------------------------------------------------


def test_classify_returns_classification_result_type() -> None:
    result = classify(_record(reason="broken"))
    assert isinstance(result, ClassificationResult)
    assert isinstance(result.category, str)
    assert isinstance(result.confidence, float)


# ---------------------------------------------------------------------------
# Structural flag priority
# ---------------------------------------------------------------------------


def test_damaged_flag_overrides_text_classification() -> None:
    """damaged=True must always produce category='damaged' regardless of reason text."""
    result = classify(_record(reason="no longer need this item", damaged=True))
    assert result.category == "damaged"
    assert result.confidence == 0.95


def test_no_damaged_flag_allows_text_classification() -> None:
    result = classify(_record(reason="no longer need this item", damaged=False))
    assert result.category == "buyer_remorse"
