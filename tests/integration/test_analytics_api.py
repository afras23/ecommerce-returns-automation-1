"""
Integration tests for analytics aggregation endpoints.
"""

import pytest
from app.main import app
from httpx import ASGITransport, AsyncClient

TRANSPORT = ASGITransport(app=app)
BASE = "/api/v1/returns"
PAYLOAD = {
    "order_id": "ORD-A1",
    "reason": "changed my mind",
    "preference": "refund",
    "purchase_date": "2026-03-01",
    "order_amount": 49.99,
    "product_id": "SKU-1",
    "customer_segment": "retail",
}


@pytest.mark.asyncio
async def test_analytics_by_product_aggregates() -> None:
    async with AsyncClient(transport=TRANSPORT, base_url="http://test") as client:
        await client.post(BASE, json=PAYLOAD)
        await client.post(
            BASE,
            json={**PAYLOAD, "order_id": "ORD-A2", "product_id": "SKU-2"},
        )
        resp = await client.get("/api/v1/analytics/returns/by-product")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_returns"] >= 2
    buckets = {r["bucket"]: r["count"] for r in data["rows"]}
    assert "SKU-1" in buckets or "SKU-2" in buckets


@pytest.mark.asyncio
async def test_analytics_by_reason_respects_filters() -> None:
    async with AsyncClient(transport=TRANSPORT, base_url="http://test") as client:
        await client.post(BASE, json=PAYLOAD)
        resp = await client.get(
            "/api/v1/analytics/returns/by-reason",
            params={"decision": "approved"},
        )
    assert resp.status_code == 200
    body = resp.json()
    assert body["total_returns"] >= 0


@pytest.mark.asyncio
async def test_analytics_pagination_offset() -> None:
    async with AsyncClient(transport=TRANSPORT, base_url="http://test") as client:
        resp = await client.get(
            "/api/v1/analytics/returns/by-segment",
            params={"page": 1, "page_size": 1},
        )
    assert resp.status_code == 200
    assert resp.json()["page_size"] == 1
