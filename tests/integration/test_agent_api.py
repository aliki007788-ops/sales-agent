# ==========================================
# tests/integration/test_agent_api.py
# ==========================================
from __future__ import annotations

import pytest
from httpx import AsyncClient


async def _tenant(client: AsyncClient) -> str:
    r = await client.post(
        "/api/v1/tenants",
        json={"name": "AgentCo", "slug": "agent-co", "plan": "pro"},
    )
    assert r.status_code == 201, r.text
    return r.json()["api_key"]


@pytest.mark.asyncio
async def test_handle_divar_event_creates_lead(client: AsyncClient) -> None:
    key = await _tenant(client)
    headers = {"X-API-Key": key}

    r = await client.post(
        "/api/v1/agent/events",
        headers=headers,
        json={
            "channel": "divar",
            "external_id": "dv-1",
            "chat_id": "dv-1",
            "text": "لپتاپ فروش\nقیمت توافقی",
            "raw": {"token": "dv-1"},
        },
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["success"] is True
    assert body["action_type"] == "create_lead"
    assert body["lead_id"] is not None

    leads = await client.get("/api/v1/leads", headers=headers)
    assert leads.status_code == 200
    assert any(x["external_id"] == "dv-1" for x in leads.json())

    events = await client.get("/api/v1/events", headers=headers)
    assert events.status_code == 200
    assert len(events.json()) >= 1


@pytest.mark.asyncio
async def test_handle_empty_message_ignored(client: AsyncClient) -> None:
    key = await _tenant(client)
    headers = {"X-API-Key": key}

    # use unique slug path — tenant already created; second tenant
    r2 = await client.post(
        "/api/v1/tenants",
        json={"name": "AgentCo2", "slug": "agent-co-2", "plan": "free"},
    )
    key2 = r2.json()["api_key"]
    headers = {"X-API-Key": key2}

    r = await client.post(
        "/api/v1/agent/events",
        headers=headers,
        json={"channel": "bale", "external_id": "e1", "chat_id": "c1", "text": "  "},
    )
    assert r.status_code == 200
    assert r.json()["action_type"] == "ignore"


@pytest.mark.asyncio
async def test_campaign_without_credentials_fails(client: AsyncClient) -> None:
    key = await _tenant(client)
    # need unique tenant
    r2 = await client.post(
        "/api/v1/tenants",
        json={"name": "CampCo", "slug": "camp-co", "plan": "pro"},
    )
    key = r2.json()["api_key"]
    headers = {"X-API-Key": key}

    r = await client.post(
        "/api/v1/agent/campaigns/start",
        headers=headers,
        json={"channel": "divar", "limit": 5},
    )
    assert r.status_code == 400
    assert "not configured" in r.json()["detail"].lower() or "credentials" in r.json()["detail"].lower()
