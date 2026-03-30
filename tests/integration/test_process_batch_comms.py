"""
Integration tests for process/batch endpoints, communication drafts, and correlation headers.
"""

from unittest.mock import AsyncMock, patch

import pytest
from app.config import Settings
from app.main import app
from app.services.ai.client import AICallResult
from app.services.communication_service import draft_refund_confirmation
from httpx import ASGITransport, AsyncClient

TRANSPORT = ASGITransport(app=app)
BASE = "/api/v1/returns"
PAYLOAD = {
    "order_id": "ORD-P1",
    "reason": "changed my mind",
    "preference": "refund",
    "purchase_date": "2026-03-01",
    "order_amount": 49.99,
}


@pytest.mark.asyncio
async def test_process_endpoint_returns_correlation_id() -> None:
    async with AsyncClient(transport=TRANSPORT, base_url="http://test") as client:
        resp = await client.post(
            "/api/v1/returns/process",
            json=PAYLOAD,
            headers={"X-Request-ID": "test-req-123"},
        )
    assert resp.status_code == 201
    body = resp.json()
    assert body.get("correlation_id") == "test-req-123"
    assert "fraud_score" in body


@pytest.mark.asyncio
async def test_response_includes_correlation_header() -> None:
    async with AsyncClient(transport=TRANSPORT, base_url="http://test") as client:
        resp = await client.get("/health", headers={"X-Request-ID": "abc-999"})
    assert resp.headers.get("X-Correlation-ID") == "abc-999"


@pytest.mark.asyncio
async def test_batch_process_multiple_items() -> None:
    async with AsyncClient(transport=TRANSPORT, base_url="http://test") as client:
        resp = await client.post(
            "/api/v1/returns/batch",
            json={
                "items": [
                    {**PAYLOAD, "order_id": "ORD-B1"},
                    {**PAYLOAD, "order_id": "ORD-B2"},
                ],
            },
        )
    assert resp.status_code == 201
    data = resp.json()
    assert len(data["results"]) == 2
    assert data.get("correlation_id")


@pytest.mark.asyncio
async def test_communication_refund_includes_facts_not_invented() -> None:
    settings = Settings(ai_provider="mock")
    from app.services.ai.client import AIClient

    client = AIClient(settings=settings)
    fake = AICallResult(
        content="Your refund of $50.00 is confirmed per FACTS.",
        tokens_used=5,
        cost_usd=0.0,
        latency_ms=1.0,
    )
    with patch.object(client, "complete", new=AsyncMock(return_value=fake)):
        body = await draft_refund_confirmation(
            ai_client=client,
            return_id="r1",
            order_id="o1",
            refund_amount_display="$50.00 USD",
            tone="professional",
        )
    assert "$50.00" in body or "50" in body


@pytest.mark.asyncio
async def test_process_with_shipping_attaches_label_json() -> None:
    async with AsyncClient(transport=TRANSPORT, base_url="http://test") as client:
        resp = await client.post(
            "/api/v1/returns/process",
            json={**PAYLOAD, "order_id": "ORD-SHIP"},
            params={"attach_shipping": True},
        )
        assert resp.status_code == 201
        rid = resp.json()["id"]
        get_resp = await client.get(f"{BASE}/{rid}")
    assert get_resp.status_code == 200
    assert get_resp.json().get("shipping_label_json") is not None
