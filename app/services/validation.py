"""
Validation: accumulates all policy violations before returning a result.
All thresholds come from config — no hardcoded business rules.
"""

from dataclasses import dataclass, field
from datetime import date

from app.config import settings
from app.models.returns import ReturnRecord


@dataclass
class ValidationResult:
    valid: bool
    reasons: list[str] = field(default_factory=list)


def validate(record: ReturnRecord) -> ValidationResult:
    """
    Run all policy checks against a return record.

    Accumulates every failure so the decision layer receives the full picture.
    Returns early only when a check blocks subsequent ones (e.g. unparseable date).

    Args:
        record: The return record to validate.

    Returns:
        ValidationResult with valid=True and empty reasons, or valid=False
        and one or more reason codes.
    """
    reasons: list[str] = []

    # 1. Return window check — exit early on parse failure
    try:
        purchase = date.fromisoformat(record.purchase_date)
    except ValueError:
        return ValidationResult(False, ["invalid_purchase_date"])

    days_since = (date.today() - purchase).days
    if days_since > settings.return_window_days:
        reasons.append(f"outside_return_window:{days_since}_days")

    # 2. Restricted product type check
    if record.product_type and record.product_type.lower() in {
        t.lower() for t in settings.restricted_product_types
    }:
        reasons.append(f"restricted_product_type:{record.product_type}")

    if reasons:
        return ValidationResult(False, reasons)

    return ValidationResult(True)
