# ==========================================
# tests/integration/test_leads.py
# ==========================================
from __future__ import annotations

import pytest
from httpx import AsyncClient


async def _api_key(client: AsyncClient) -> str:
    r = await client.post(
        "/api/v1/tenants",
        json={"name": "LeadCo", "slug": "lead-co", "plan": "pro"},
    )
    assert r.status_code == 201, r.text
    return r.json()["api_key"]


@pytest.mark.asyncio
async def test_create_and_list_leads(client: AsyncClient) -> None:
    key = await _api_key(client)
    headers = {"X-API-Key": key}

    r = await client.post(
        "/api/v1/leads",
        headers=headers,
        json={
            "source": "divar",
            "external_id": "post-99",
            "name": "آیفون",
            "score": 10,
            "notes": "تست",
        },
    )
    assert r.status_code == 201, r.text
    lead = r.json()
    assert lead["source"] == "divar"
    assert lead["external_id"] == "post-99"
    lead_id = lead["id"]

    listed = await client.get("/api/v1/leads", headers=headers)
    assert listed.status_code == 200
    assert any(x["id"] == lead_id for x in listed.json())

    one = await client.get(f"/api/v1/leads/{lead_id}", headers=headers)
    assert one.status_code == 200
    assert one.json()["name"] == "آیفون"

    patched = await client.patch(
        f"/api/v1/leads/{lead_id}",
        headers=headers,
        json={"status": "contacted", "score": 50},
    )
    assert patched.status_code == 200
    assert patched.json()["status"] == "contacted"
    assert patched.json()["score"] == 50


@pytest.mark.asyncio
async def test_leads_require_auth(client: AsyncClient) -> None:
    r = await client.get("/api/v1/leads")
    assert r.status_code in (401, 422)
