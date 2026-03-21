"""
Integration tests for the full return processing pipeline.
Each test exercises the entire request → decision → DB path.
"""

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.metrics import metrics
from app.main import app

BASE = "/api/v1/returns"
TRANSPORT = ASGITransport(app=app)

# A base payload that is always within the return window
_BASE = {
    "order_id": "ORD-TEST-001",
    "reason": "Item arrived in perfect condition but changed my mind",
    "preference": "refund",
    "purchase_date": "2026-03-01",
    "damaged": False,
    "order_amount": 49.99,
}


def _payload(**overrides) -> dict:
    return {**_BASE, **overrides}


# ---------------------------------------------------------------------------
# Decision: approved
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_standard_return_is_approved():
    async with AsyncClient(transport=TRANSPORT, base_url="http://test") as client:
        resp = await client.post(BASE, json=_payload())
    assert resp.status_code == 201
    body = resp.json()
    assert body["decision"] == "approved"
    assert body["routing_outcome"] == "finance:refund_processing"


@pytest.mark.asyncio
async def test_exchange_preference_routes_to_warehouse():
    async with AsyncClient(transport=TRANSPORT, base_url="http://test") as client:
        resp = await client.post(BASE, json=_payload(preference="exchange"))
    assert resp.status_code == 201
    body = resp.json()
    assert body["decision"] == "approved"
    assert body["routing_outcome"] == "warehouse:exchange_processing"


# ---------------------------------------------------------------------------
# Decision: rejected
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_return_outside_window_is_rejected():
    async with AsyncClient(transport=TRANSPORT, base_url="http://test") as client:
        resp = await client.post(BASE, json=_payload(purchase_date="2025-01-01"))
    assert resp.status_code == 201
    body = resp.json()
    assert body["decision"] == "rejected"
    assert "outside_return_window" in body["decision_reason"]
    assert body["routing_outcome"] == "notify_customer:rejected"


@pytest.mark.asyncio
async def test_invalid_purchase_date_is_rejected():
    async with AsyncClient(transport=TRANSPORT, base_url="http://test") as client:
        resp = await client.post(BASE, json=_payload(purchase_date="not-a-date"))
    assert resp.status_code == 201
    assert resp.json()["decision"] == "rejected"


# ---------------------------------------------------------------------------
# Decision: manual_review
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_damaged_item_goes_to_manual_review():
    async with AsyncClient(transport=TRANSPORT, base_url="http://test") as client:
        resp = await client.post(BASE, json=_payload(damaged=True, reason="Item is broken"))
    assert resp.status_code == 201
    body = resp.json()
    assert body["decision"] == "manual_review"
    assert body["routing_outcome"] == "damage_claims_team"


@pytest.mark.asyncio
async def test_wrong_item_goes_to_warehouse_investigation():
    async with AsyncClient(transport=TRANSPORT, base_url="http://test") as client:
        resp = await client.post(
            BASE,
            json=_payload(reason="This is the wrong item, I ordered something else"),
        )
    assert resp.status_code == 201
    body = resp.json()
    assert body["decision"] == "manual_review"
    assert body["routing_outcome"] == "warehouse_investigation"


@pytest.mark.asyncio
async def test_high_value_order_goes_to_manual_review():
    async with AsyncClient(transport=TRANSPORT, base_url="http://test") as client:
        resp = await client.post(BASE, json=_payload(order_amount=999.99))
    assert resp.status_code == 201
    body = resp.json()
    assert body["decision"] == "manual_review"
    assert body["decision_reason"] == "high_value_order"


# ---------------------------------------------------------------------------
# Retrieval
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_return_by_id():
    async with AsyncClient(transport=TRANSPORT, base_url="http://test") as client:
        create_resp = await client.post(BASE, json=_payload())
        return_id = create_resp.json()["id"]
        get_resp = await client.get(f"{BASE}/{return_id}")
    assert get_resp.status_code == 200
    body = get_resp.json()
    assert body["id"] == return_id
    assert body["order_id"] == "ORD-TEST-001"


@pytest.mark.asyncio
async def test_get_nonexistent_return_returns_404():
    async with AsyncClient(transport=TRANSPORT, base_url="http://test") as client:
        resp = await client.get(f"{BASE}/does-not-exist")
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Metrics
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_metrics_are_recorded():
    async with AsyncClient(transport=TRANSPORT, base_url="http://test") as client:
        await client.post(BASE, json=_payload())                           # approved
        await client.post(BASE, json=_payload(purchase_date="2025-01-01"))  # rejected
        await client.post(BASE, json=_payload(damaged=True))               # manual_review
        resp = await client.get("/metrics")

    body = resp.json()
    assert body["total"] == 3
    assert body["approved"] == 1
    assert body["rejected"] == 1
    assert body["manual_review"] == 1
    assert body["approval_rate"] == pytest.approx(1 / 3, abs=1e-4)
