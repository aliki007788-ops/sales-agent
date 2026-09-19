# ==========================================
# tests/integration/test_credentials_webhook.py
# ==========================================
from __future__ import annotations

import pytest
from httpx import AsyncClient


async def _tenant(client: AsyncClient, slug: str) -> tuple[str, str]:
    r = await client.post(
        "/api/v1/tenants",
        json={"name": slug, "slug": slug, "plan": "pro"},
    )
    assert r.status_code == 201, r.text
    data = r.json()
    return data["id"], data["api_key"]


@pytest.mark.asyncio
async def test_store_and_list_credentials(client: AsyncClient) -> None:
    _tid, key = await _tenant(client, "cred-co")
    headers = {"X-API-Key": key}

    r = await client.post(
        "/api/v1/agent/channels/bale/credentials",
        headers=headers,
        json={"credentials": {"token": "111:SECRET"}, "webhook_secret": "whsec-1"},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["channel"] == "bale"
    assert body["webhook_secret"] == "whsec-1"
    assert "token" not in body  # never expose secrets

    listed = await client.get("/api/v1/agent/channels", headers=headers)
    assert listed.status_code == 200
    assert any(c["channel"] == "bale" for c in listed.json())


@pytest.mark.asyncio
async def test_webhook_creates_lead(client: AsyncClient) -> None:
    tid, key = await _tenant(client, "hook-co")
    headers = {"X-API-Key": key}

    await client.post(
        "/api/v1/agent/channels/divar/credentials",
        headers=headers,
        json={"credentials": {"city": "tehran"}, "webhook_secret": "sec-divar"},
    )

    # Public webhook — no API key, uses secret
    r = await client.post(
        f"/api/v1/webhooks/{tid}/divar",
        headers={"X-Webhook-Secret": "sec-divar"},
        json={
            "id": "post-55",
            "chat_id": "post-55",
            "text": "گوشی سامسونگ\nنو",
        },
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["success"] is True
    assert body["action_type"] == "create_lead"
    assert body["lead_id"] is not None

    leads = await client.get("/api/v1/leads", headers=headers)
    assert any(x["external_id"] == "post-55" for x in leads.json())


@pytest.mark.asyncio
async def test_webhook_rejects_bad_secret(client: AsyncClient) -> None:
    tid, key = await _tenant(client, "hook-bad")
    headers = {"X-API-Key": key}
    await client.post(
        "/api/v1/agent/channels/bale/credentials",
        headers=headers,
        json={"credentials": {"token": "x:y"}, "webhook_secret": "correct"},
    )

    r = await client.post(
        f"/api/v1/webhooks/{tid}/bale",
        headers={"X-Webhook-Secret": "wrong"},
        json={"message": {"text": "hi", "chat": {"id": 1}}},
    )
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_queue_depth() -> None:
    from sales_agent.worker.queue import InMemoryQueue

    q = InMemoryQueue()
    assert q.depth == 0
    await q.enqueue("noop", {"x": 1})
    assert q.depth == 1
