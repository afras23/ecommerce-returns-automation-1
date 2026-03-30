"""
Rule-based refund calculation from product condition (no AI).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from app.services.product_condition_service import ProductCondition

if TYPE_CHECKING:
    from app.config import Settings


@dataclass(frozen=True)
class RefundComputationInput:
    """Inputs for deterministic refund math."""

    order_amount: float
    condition: ProductCondition


@dataclass(frozen=True)
class RefundComputationOutput:
    """Refund amount breakdown."""

    refund_amount: float
    percentage: float
    fees: float
    reason: str


REFUND_PERCENT_BY_CONDITION: dict[ProductCondition, float] = {
    ProductCondition.UNOPENED: 1.0,
    ProductCondition.OPENED_UNUSED: 0.5,
    ProductCondition.USED: 0.3,
    ProductCondition.DAMAGED_BY_CUSTOMER: 0.0,
}


def compute_refund(
    data: RefundComputationInput,
    *,
    settings: Settings,
) -> RefundComputationOutput:
    """
    Compute refund using fixed condition → percentage mapping and optional restocking fee.

    Args:
        data: Order amount and assessed product condition.
        settings: Includes ``restocking_fee_percent`` applied to the order amount.

    Returns:
        RefundComputationOutput with rounded monetary fields.
    """
    if data.order_amount < 0:
        raise ValueError("order_amount must be non-negative")

    pct = REFUND_PERCENT_BY_CONDITION[data.condition]
    fee_rate = max(0.0, settings.restocking_fee_percent)
    gross = round(data.order_amount * pct, 2)
    fees = round(data.order_amount * fee_rate, 2)
    refund_amount = round(max(0.0, gross - fees), 2)

    reason = (
        f"condition={data.condition.value}; base_pct={pct:.2f}; restocking_fee_pct={fee_rate:.4f}"
    )

    return RefundComputationOutput(
        refund_amount=refund_amount,
        percentage=pct,
        fees=fees,
        reason=reason,
    )
