"""
Edge-case refund math: extreme magnitudes and boundary amounts.
"""

import pytest
from app.config import Settings
from app.services.product_condition_service import ProductCondition
from app.services.refund_service import RefundComputationInput, compute_refund


@pytest.mark.parametrize(
    ("order_amount", "condition", "expected_pct"),
    [
        (0.0, ProductCondition.UNOPENED, 1.0),
        (9_999_999.99, ProductCondition.OPENED_UNUSED, 0.5),
        (1e-6, ProductCondition.USED, 0.3),
    ],
)
def test_refund_extreme_amounts_respect_percentages(
    order_amount: float,
    condition: ProductCondition,
    expected_pct: float,
) -> None:
    settings = Settings(restocking_fee_percent=0.0)
    out = compute_refund(
        RefundComputationInput(order_amount=order_amount, condition=condition),
        settings=settings,
    )
    assert out.percentage == expected_pct
    assert out.refund_amount >= 0.0
    assert out.refund_amount == pytest.approx(round(order_amount * expected_pct, 2))


def test_refund_extreme_with_restocking_fee() -> None:
    settings = Settings(restocking_fee_percent=0.15)
    out = compute_refund(
        RefundComputationInput(order_amount=1_000_000.0, condition=ProductCondition.UNOPENED),
        settings=settings,
    )
    assert out.fees == pytest.approx(150_000.0)
    assert out.refund_amount == pytest.approx(850_000.0)


@pytest.mark.parametrize("bad", [-0.01, -1e9])
def test_refund_rejects_negative_order_amount(bad: float) -> None:
    settings = Settings()
    with pytest.raises(ValueError, match="non-negative"):
        compute_refund(
            RefundComputationInput(order_amount=bad, condition=ProductCondition.USED),
            settings=settings,
        )
