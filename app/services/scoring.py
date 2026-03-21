"""
Scoring: produces a composite risk/confidence score (0.0 – 1.0) for a return.

A higher score means we are MORE confident the return is legitimate and
straightforward — making it a better candidate for auto-approval.

Score components
----------------
classification_factor  (weight 0.35)
    How confident the classifier is about the reason category.

value_factor           (weight 0.15)
    Higher-value orders introduce more financial risk, reducing the score.

clarity_factor         (weight 0.40)
    How objectively verifiable and auto-processable the category is.
    Damaged / wrong-item require physical verification → low clarity.
    Buyer remorse / sizing are policy-standard → high clarity.

history_factor         (weight 0.10)
    Simulated return-history signal. Pluggable for a real DB lookup.
    Defaults to 1.0 (no negative history on record).
"""

from dataclasses import dataclass

from app.models.returns import ReturnRecord
from app.services.classification import ClassificationResult
from app.services.validation import ValidationResult

# Weights must sum to 1.0
_WEIGHTS: dict[str, float] = {
    "classification": 0.35,
    "value":          0.15,
    "clarity":        0.40,
    "history":        0.10,
}

# How objectively auto-processable each category is (0 = always needs human)
_CLARITY_FACTOR: dict[str, float] = {
    "damaged":          0.10,  # physical inspection required
    "wrong_item":       0.25,  # warehouse verification required
    "not_as_described": 0.25,  # subjective dispute — always warrants human judgment
    "buyer_remorse":    0.85,  # clear, policy-standard
    "sizing":           0.90,  # objective, common case
    "other":            0.20,  # unknown reason — treat cautiously
}


@dataclass
class ScoreResult:
    score: float               # composite 0.0 – 1.0
    classification_factor: float
    value_factor: float
    clarity_factor: float
    history_factor: float


def score(
    record: ReturnRecord,
    validation: ValidationResult,
    classification: ClassificationResult,
) -> ScoreResult:
    """
    Compute a composite confidence score for a return request.

    Invalid returns receive score=0.0 immediately; the decision layer
    handles rejection — this function does not need to replicate that logic.

    Args:
        record: The return record (provides order_amount for value factor).
        validation: Result of the policy validation step.
        classification: Result of the reason classification step.

    Returns:
        ScoreResult with composite score and per-factor breakdown.
    """
    if not validation.valid:
        return ScoreResult(
            score=0.0,
            classification_factor=0.0,
            value_factor=0.0,
            clarity_factor=0.0,
            history_factor=0.0,
        )

    classification_factor = classification.confidence

    # Value factor: higher order amounts introduce more financial exposure
    amount = record.order_amount or 0.0
    from app.config import settings  # local import avoids circular at module level
    if amount > settings.refund_threshold_amount:
        value_factor = 0.50
    elif amount > settings.refund_threshold_amount * 0.5:
        value_factor = 0.75
    else:
        value_factor = 1.0

    clarity_factor = _CLARITY_FACTOR.get(classification.category, 0.20)

    # Simulated history: 1.0 = no negative history on record.
    # In a real system this would be a DB lookup (serial returner score, etc.)
    history_factor = _simulate_history(record)

    composite = (
        _WEIGHTS["classification"] * classification_factor
        + _WEIGHTS["value"]          * value_factor
        + _WEIGHTS["clarity"]        * clarity_factor
        + _WEIGHTS["history"]        * history_factor
    )

    return ScoreResult(
        score=round(composite, 4),
        classification_factor=round(classification_factor, 4),
        value_factor=round(value_factor, 4),
        clarity_factor=round(clarity_factor, 4),
        history_factor=round(history_factor, 4),
    )


def _simulate_history(_record: ReturnRecord) -> float:
    """
    Return a history factor for this customer.

    Returns 1.0 (clean record) by default — no negative history on file.
    Replace the body with a real DB query when customer history is available.
    The record parameter provides order_id / customer_email for the lookup.
    """
    return 1.0
