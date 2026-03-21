"""
Unit tests for the validation service.

All tests create ReturnRecord objects directly — no database required.
"""

import pytest

from app.models.returns import ReturnRecord
from app.services.validation import validate


def _record(**kwargs) -> ReturnRecord:
    defaults = {
        "id": "test",
        "order_id": "ORD-001",
        "reason": "changed my mind",
        "preference": "refund",
        "purchase_date": "2026-03-01",  # 20 days before today (2026-03-21)
        "order_amount": 49.99,
        "damaged": False,
        "product_type": None,
    }
    return ReturnRecord(**{**defaults, **kwargs})


# ---------------------------------------------------------------------------
# Return window
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "purchase_date,expected_valid",
    [
        ("2026-03-01", True),   # 20 days ago — within 30-day window
        ("2026-03-20", True),   # 1 day ago — well within window
        ("2025-12-22", False),  # ~89 days ago — outside the 30-day window
        ("2025-01-01", False),  # ~14 months ago — far outside
        ("2026-02-19", True),   # 30 days ago — boundary (inclusive)
    ],
)
def test_return_window_boundary(purchase_date: str, expected_valid: bool) -> None:
    result = validate(_record(purchase_date=purchase_date))
    assert result.valid == expected_valid


def test_outside_window_includes_day_count_in_reason() -> None:
    result = validate(_record(purchase_date="2025-01-01"))
    assert not result.valid
    assert any("outside_return_window" in r for r in result.reasons)
    assert any("days" in r for r in result.reasons)


# ---------------------------------------------------------------------------
# Invalid purchase date
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "bad_date",
    ["not-a-date", "2026/03/01", "01-03-2026", "", "yesterday", "2026-13-01"],
)
def test_unparseable_purchase_date_is_rejected(bad_date: str) -> None:
    result = validate(_record(purchase_date=bad_date))
    assert not result.valid
    assert result.reasons == ["invalid_purchase_date"]


# ---------------------------------------------------------------------------
# Restricted product types
# ---------------------------------------------------------------------------


def test_restricted_product_type_fails_validation(monkeypatch) -> None:
    from app.services import validation as val_mod

    monkeypatch.setattr(val_mod.settings, "restricted_product_types", ["digital"])
    result = validate(_record(product_type="digital"))
    assert not result.valid
    assert any("restricted_product_type" in r for r in result.reasons)


def test_restriction_check_is_case_insensitive(monkeypatch) -> None:
    from app.services import validation as val_mod

    monkeypatch.setattr(val_mod.settings, "restricted_product_types", ["digital"])
    result = validate(_record(product_type="Digital"))
    assert not result.valid


def test_unrestricted_product_type_passes(monkeypatch) -> None:
    from app.services import validation as val_mod

    monkeypatch.setattr(val_mod.settings, "restricted_product_types", ["digital"])
    result = validate(_record(product_type="clothing"))
    assert result.valid


def test_no_product_type_always_passes() -> None:
    result = validate(_record(product_type=None))
    assert result.valid


# ---------------------------------------------------------------------------
# Multiple failures are accumulated
# ---------------------------------------------------------------------------


def test_all_failures_are_reported_together(monkeypatch) -> None:
    """A return outside window AND with a restricted product type reports both reasons."""
    from app.services import validation as val_mod

    monkeypatch.setattr(val_mod.settings, "restricted_product_types", ["digital"])
    result = validate(_record(purchase_date="2025-01-01", product_type="digital"))
    assert not result.valid
    assert len(result.reasons) == 2
    assert any("outside_return_window" in r for r in result.reasons)
    assert any("restricted_product_type" in r for r in result.reasons)


# ---------------------------------------------------------------------------
# Happy path
# ---------------------------------------------------------------------------


def test_valid_return_has_empty_reasons() -> None:
    result = validate(_record())
    assert result.valid
    assert result.reasons == []
