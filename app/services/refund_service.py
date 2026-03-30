"""
Refund orchestration service interface (financial side effects).

Coordinates approvals with payment and finance systems — not implemented here.
"""

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class RefundRequestInput:
    """Parameters to initiate a refund."""

    return_id: str
    order_id: str
    amount_usd: float | None


@dataclass(frozen=True)
class RefundRequestOutput:
    """Result of a refund initiation attempt."""

    status: str  # pending | completed | failed
    reference: str | None


class RefundService(Protocol):
    """
    Initiates and tracks refund execution.

    Expected behavior:
        - Idempotent per return_id where the downstream provider allows.
        - Never double-refund without explicit reconciliation.
    """

    def initiate_refund(self, data: RefundRequestInput) -> RefundRequestOutput:
        ...
