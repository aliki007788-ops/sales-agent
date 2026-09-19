# ==========================================
# tests/integration/test_tenants.py
# ==========================================
from __future__ import annotations

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_create_and_authenticate(client: AsyncClient) -> None:
    r = await client.post(
        "/api/v1/tenants",
        json={"name": "Acme", "slug": "acme", "plan": "pro"},
    )
    assert r.status_code == 201, r.text
    data = r.json()
    api_key = data["api_key"]
    assert api_key.startswith("asa_")
    assert data["slug"] == "acme"

    me = await client.get("/api/v1/tenants/me", headers={"X-API-Key": api_key})
    assert me.status_code == 200
    assert me.json()["slug"] == "acme"


@pytest.mark.asyncio
async def test_duplicate_slug_conflict(client: AsyncClient) -> None:
    payload = {"name": "Beta", "slug": "beta", "plan": "free"}
    r1 = await client.post("/api/v1/tenants", json=payload)
    assert r1.status_code == 201
    r2 = await client.post("/api/v1/tenants", json=payload)
    assert r2.status_code == 409


@pytest.mark.asyncio
async def test_wrong_api_key_rejected(client: AsyncClient) -> None:
    r = await client.get(
        "/api/v1/tenants/me", headers={"X-API-Key": "asa_invalid-key-here"}
    )
    assert r.status_code == 401
