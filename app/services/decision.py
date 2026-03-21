"""
Decision: produces approve / reject / manual_review given validation + classification.
All thresholds are read from config.
"""

from dataclasses import dataclass

from app.config import settings
from app.models.returns import ReturnRecord
from app.services.validation import ValidationResult


@dataclass
class DecisionResult:
    decision: str  # approved | rejected | manual_review
    reason: str


def decide(
    record: ReturnRecord,
    validation: ValidationResult,
    classification: str,
) -> DecisionResult:
    # Failed policy validation → reject immediately
    if not validation.valid:
        return DecisionResult("rejected", validation.reason)

    # High-value orders need a human
    if (
        record.order_amount is not None
        and record.order_amount > settings.refund_threshold_amount
        and settings.high_value_manual_review
    ):
        return DecisionResult("manual_review", "high_value_order")

    # Physical damage requires inspection
    if classification == "damaged":
        return DecisionResult("manual_review", "damage_claim")

    # Wrong-item shipments require warehouse investigation
    if classification == "wrong_item":
        return DecisionResult("manual_review", "wrong_item_claim")

    # Everything else within the window is auto-approved
    return DecisionResult("approved", f"standard:{classification}")
