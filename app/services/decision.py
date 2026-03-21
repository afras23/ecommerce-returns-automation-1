"""
Decision: maps a validation result + composite score to a final decision.

Two explicit hard rules override the score-based path:
  1. Validation failure → always REJECT (score is irrelevant)
  2. High-value order → always MANUAL_REVIEW (hard business rule from config)

All other decisions are score-based using the auto_approve_score threshold.
"""

from dataclasses import dataclass

from app.config import settings
from app.models.returns import ReturnRecord
from app.services.scoring import ScoreResult
from app.services.validation import ValidationResult


@dataclass
class DecisionResult:
    decision: str  # approved | rejected | manual_review
    reason: str


def decide(
    record: ReturnRecord,
    validation: ValidationResult,
    score: ScoreResult,
) -> DecisionResult:
    """
    Produce the final return decision.

    Args:
        record: The return record (provides order_amount for value check).
        validation: Accumulated policy validation results.
        score: Composite confidence score from the scoring step.

    Returns:
        DecisionResult with the decision and a machine-readable reason code.
    """
    # 1. Policy validation failure → reject, include all reasons
    if not validation.valid:
        return DecisionResult(
            "rejected",
            "validation_failed:" + ";".join(validation.reasons),
        )

    # 2. High-value orders → mandatory human review (explicit business rule)
    if (
        record.order_amount is not None
        and record.order_amount > settings.refund_threshold_amount
        and settings.high_value_manual_review
    ):
        return DecisionResult("manual_review", "high_value_order")

    # 3. Score-based gate
    if score.score >= settings.auto_approve_score:
        return DecisionResult("approved", f"score:{score.score:.3f}")

    return DecisionResult("manual_review", f"low_confidence_score:{score.score:.3f}")
