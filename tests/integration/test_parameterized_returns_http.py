"""
Parameterized HTTP return scenarios (deterministic pipeline outcomes).
"""

import pytest
from app.main import app
from httpx import ASGITransport, AsyncClient

BASE = "/api/v1/returns"
TRANSPORT = ASGITransport(app=app)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("reason", "damaged", "expected_decision_substring"),
    [
        ("changed my mind — no longer need it", False, "approved"),
        ("arrived damaged and scratched", False, "manual_review"),
        ("this is nonsense qwerty zxcv", False, "manual_review"),
    ],
)
async def test_return_outcomes_by_reason_profile(
    reason: str,
    damaged: bool,
    expected_decision_substring: str,
) -> None:
    async with AsyncClient(transport=TRANSPORT, base_url="http://test") as client:
        resp = await client.post(
            BASE,
            json={
                "order_id": f"ORD-P-{hash(reason) % 10000}",
                "reason": reason,
                "preference": "refund",
                "purchase_date": "2026-03-01",
                "order_amount": 40.0,
                "damaged": damaged,
            },
        )
    assert resp.status_code == 201
    body = resp.json()
    assert expected_decision_substring in body["decision"].lower()


@pytest.mark.asyncio
@pytest.mark.parametrize("preference", ["refund", "exchange"])
async def test_preference_routing_differs(preference: str) -> None:
    async with AsyncClient(transport=TRANSPORT, base_url="http://test") as client:
        resp = await client.post(
            BASE,
            json={
                "order_id": f"ORD-PREF-{preference}",
                "reason": "changed my mind",
                "preference": preference,
                "purchase_date": "2026-03-01",
                "order_amount": 30.0,
            },
        )
    assert resp.status_code == 201
    out = resp.json()["routing_outcome"]
    if preference == "exchange":
        assert "warehouse" in out.lower()
    else:
        assert "finance" in out.lower() or "refund" in out.lower()
