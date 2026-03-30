"""
Concurrent return submissions: many parallel requests against the same test app DB.
"""

import asyncio

import pytest
from app.main import app
from httpx import ASGITransport, AsyncClient

BASE = "/api/v1/returns"
TRANSPORT = ASGITransport(app=app)

_PAYLOAD = {
    "reason": "changed my mind",
    "preference": "refund",
    "purchase_date": "2026-03-01",
    "order_amount": 29.99,
}


@pytest.mark.asyncio
async def test_parallel_posts_all_succeed_and_persist() -> None:
    async with AsyncClient(transport=TRANSPORT, base_url="http://test") as client:

        async def one(idx: int) -> tuple[int, str]:
            resp = await client.post(
                BASE,
                json={**_PAYLOAD, "order_id": f"ORD-CONC-{idx}"},
            )
            body = resp.json()
            return resp.status_code, body.get("id", "")

        results = await asyncio.gather(*[one(i) for i in range(12)])
    assert all(status == 201 for status, _ in results)
    ids = {rid for _, rid in results}
    assert len(ids) == 12
    assert all(rid for rid in ids)


@pytest.mark.asyncio
async def test_parallel_reads_after_writes() -> None:
    async with AsyncClient(transport=TRANSPORT, base_url="http://test") as client:
        created = await client.post(
            BASE,
            json={**_PAYLOAD, "order_id": "ORD-READ-1"},
        )
        rid = created.json()["id"]

        async def fetch() -> int:
            r = await client.get(f"{BASE}/{rid}")
            return r.status_code

        codes = await asyncio.gather(*[fetch() for _ in range(8)])
    assert all(c == 200 for c in codes)
