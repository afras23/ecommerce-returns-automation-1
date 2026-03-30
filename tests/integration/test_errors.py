"""
Tests for global error response shape.
"""

import pytest
from app.main import app
from httpx import ASGITransport, AsyncClient


@pytest.mark.asyncio
async def test_validation_error_json_shape() -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/api/v1/returns",
            json={"order_id": "ORD-1"},
        )
    assert resp.status_code == 422
    body = resp.json()
    assert body["error"]["code"] == "VALIDATION_ERROR"
    assert "request_id" in body["error"]


@pytest.mark.asyncio
async def test_not_found_error_json_shape() -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/v1/returns/does-not-exist-uuid")
    assert resp.status_code == 404
    body = resp.json()
    assert body["error"]["code"] == "HTTP_ERROR"
    assert "not found" in body["error"]["message"].lower()
