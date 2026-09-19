import pytest
from httpx import AsyncClient


async def _key(client: AsyncClient, slug: str) -> str:
    r = await client.post(
        "/api/v1/tenants",
        json={"name": slug, "slug": slug, "plan": "pro"},
    )
    assert r.status_code == 201
    return r.json()["api_key"]


@pytest.mark.asyncio
async def test_plans_and_usage(client: AsyncClient):
    key = await _key(client, "bill-co")
    r = await client.get("/api/v1/billing/plans")
    assert r.status_code == 200
    assert any(p["name"] == "pro" for p in r.json())

    u = await client.get("/api/v1/billing/usage", headers={"X-API-Key": key})
    assert u.status_code == 200
    assert u.json()["plan"] == "pro"


@pytest.mark.asyncio
async def test_add_team_member(client: AsyncClient):
    key = await _key(client, "team-co")
    r = await client.post(
        "/api/v1/team",
        headers={"X-API-Key": key},
        json={"email": "a@x.com", "role": "agent", "display_name": "Ali"},
    )
    assert r.status_code == 201, r.text
    listed = await client.get("/api/v1/team", headers={"X-API-Key": key})
    assert listed.status_code == 200
    assert len(listed.json()) == 1
