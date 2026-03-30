"""
Routing: maps a decision + classification to the downstream team or system.

Manual-review destinations are driven by classification category so that
the routing is not fragile string-matching against decision reason codes.
"""

from app.models.returns import ReturnRecord
from app.services.classification import ClassificationResult
from app.services.decision import DecisionResult

# Which queue receives each category when the decision is manual_review
_CATEGORY_QUEUE: dict[str, str] = {
    "damaged": "damage_claims_team",
    "wrong_item": "warehouse_investigation",
    "not_as_described": "customer_disputes_team",
    "buyer_remorse": "manual_review_queue",
    "sizing": "manual_review_queue",
    "other": "manual_review_queue",
}


def route(
    record: ReturnRecord,
    classification: ClassificationResult,
    decision: DecisionResult,
) -> str:
    """
    Determine the routing destination for a processed return.

    Args:
        record: The return record (provides preference for approved routing).
        classification: Used to select the right manual-review queue.
        decision: The final decision outcome.

    Returns:
        A string identifier for the downstream system or team.
    """
    if decision.decision == "rejected":
        return "notify_customer:rejected"

    if decision.decision == "manual_review":
        # High-value orders bypass category routing → senior escalation
        if "high_value" in decision.reason:
            return "senior_support_review"
        return _CATEGORY_QUEUE.get(classification.category, "manual_review_queue")

    # approved
    if record.preference == "exchange":
        return "warehouse:exchange_processing"
    return "finance:refund_processing"
