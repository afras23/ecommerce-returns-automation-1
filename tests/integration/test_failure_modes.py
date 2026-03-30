"""
Failure modes: malformed input, validation errors, and malformed batches.
"""

import pytest
from app.main import app
from httpx import ASGITransport, AsyncClient

BASE = "/api/v1/returns"
TRANSPORT = ASGITransport(app=app)


@pytest.mark.asyncio
async def test_malformed_json_body_returns_422() -> None:
    async with AsyncClient(transport=TRANSPORT, base_url="http://test") as client:
        resp = await client.post(
            BASE,
            content="{not valid json",
            headers={"Content-Type": "application/json"},
        )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_invalid_json_type_order_amount_returns_422() -> None:
    async with AsyncClient(transport=TRANSPORT, base_url="http://test") as client:
        resp = await client.post(
            BASE,
            json={
                "order_id": "O1",
                "reason": "changed my mind",
                "preference": "refund",
                "purchase_date": "2026-03-01",
                "order_amount": "not-a-number",
            },
        )
    assert resp.status_code == 422
    assert resp.json()["error"]["code"] == "VALIDATION_ERROR"


@pytest.mark.asyncio
async def test_batch_empty_items_returns_422() -> None:
    async with AsyncClient(transport=TRANSPORT, base_url="http://test") as client:
        resp = await client.post(f"{BASE}/batch", json={"items": []})
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_invalid_preference_pattern_returns_422() -> None:
    async with AsyncClient(transport=TRANSPORT, base_url="http://test") as client:
        resp = await client.post(
            BASE,
            json={
                "order_id": "O1",
                "reason": "changed my mind",
                "preference": "store_credit",
                "purchase_date": "2026-03-01",
            },
        )
    assert resp.status_code == 422
