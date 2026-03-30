"""
Unit tests for rule-based refund computation.
"""

import pytest
from app.config import Settings
from app.services.product_condition_service import ProductCondition
from app.services.refund_service import RefundComputationInput, compute_refund


def test_refund_unopened_full() -> None:
    settings = Settings(restocking_fee_percent=0.0)
    out = compute_refund(
        RefundComputationInput(order_amount=100.0, condition=ProductCondition.UNOPENED),
        settings=settings,
    )
    assert out.percentage == 1.0
    assert out.refund_amount == pytest.approx(100.0)
    assert out.fees == pytest.approx(0.0)


def test_refund_opened_half() -> None:
    settings = Settings(restocking_fee_percent=0.0)
    out = compute_refund(
        RefundComputationInput(order_amount=80.0, condition=ProductCondition.OPENED_UNUSED),
        settings=settings,
    )
    assert out.percentage == 0.5
    assert out.refund_amount == pytest.approx(40.0)


def test_refund_damaged_zero() -> None:
    settings = Settings(restocking_fee_percent=0.0)
    out = compute_refund(
        RefundComputationInput(
            order_amount=99.0,
            condition=ProductCondition.DAMAGED_BY_CUSTOMER,
        ),
        settings=settings,
    )
    assert out.refund_amount == pytest.approx(0.0)


def test_restocking_fee_reduces_refund() -> None:
    settings = Settings(restocking_fee_percent=0.1)
    out = compute_refund(
        RefundComputationInput(order_amount=100.0, condition=ProductCondition.UNOPENED),
        settings=settings,
    )
    assert out.fees == pytest.approx(10.0)
    assert out.refund_amount == pytest.approx(90.0)


def test_refund_invalid_amount() -> None:
    settings = Settings()
    with pytest.raises(ValueError):
        compute_refund(
            RefundComputationInput(order_amount=-1.0, condition=ProductCondition.USED),
            settings=settings,
        )
