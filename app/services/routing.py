"""
Routing: maps a decision to the downstream team or system that should act on it.
"""

from app.models.returns import ReturnRecord
from app.services.decision import DecisionResult


def route(record: ReturnRecord, decision: DecisionResult) -> str:
    if decision.decision == "rejected":
        return "notify_customer:rejected"

    if decision.decision == "manual_review":
        reason = decision.reason
        if "damage" in reason:
            return "damage_claims_team"
        if "wrong_item" in reason:
            return "warehouse_investigation"
        if "high_value" in reason:
            return "senior_support_review"
        return "manual_review_queue"

    # approved
    if record.preference == "exchange":
        return "warehouse:exchange_processing"
    return "finance:refund_processing"
