"""
Validation: policy checks that must pass before a return can be approved.
All thresholds come from config — no hardcoded business rules.
"""

from dataclasses import dataclass
from datetime import date

from app.config import settings
from app.models.returns import ReturnRecord


@dataclass
class ValidationResult:
    valid: bool
    reason: str = ""


def validate(record: ReturnRecord) -> ValidationResult:
    # 1. Return window check
    try:
        purchase = date.fromisoformat(record.purchase_date)
    except ValueError:
        return ValidationResult(False, "invalid_purchase_date")

    days_since = (date.today() - purchase).days
    if days_since > settings.return_window_days:
        return ValidationResult(
            False, f"outside_return_window:{days_since}_days"
        )

    # 2. Restricted product type check
    if record.product_type and record.product_type.lower() in [
        t.lower() for t in settings.restricted_product_types
    ]:
        return ValidationResult(
            False, f"restricted_product_type:{record.product_type}"
        )

    return ValidationResult(True)
