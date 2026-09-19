import pytest
import pyotp
from httpx import AsyncClient


async def _key(client: AsyncClient, slug: str) -> str:
    r = await client.post(
        "/api/v1/tenants",
        json={"name": slug, "slug": slug, "plan": "pro"},
    )
    assert r.status_code == 201
    return r.json()["api_key"]


@pytest.mark.asyncio
async def test_totp_enroll_and_verify(client: AsyncClient):
    key = await _key(client, "sec-totp")
    headers = {"X-API-Key": key}
    r = await client.post(
        "/api/v1/security/totp/enroll",
        headers=headers,
        json={"email": "u@x.com"},
    )
    assert r.status_code == 200, r.text
    secret = r.json()["secret"]
    code = pyotp.TOTP(secret).now()
    v = await client.post(
        "/api/v1/security/totp/verify",
        headers=headers,
        json={"email": "u@x.com", "code": code},
    )
    assert v.status_code == 200
    assert v.json()["valid"] is True


@pytest.mark.asyncio
async def test_session_revoke(client: AsyncClient):
    key = await _key(client, "sec-sess")
    headers = {"X-API-Key": key}
    r = await client.post(
        "/api/v1/security/sessions/revoke",
        headers=headers,
        json={"jti": "jti-test-12345", "reason": "logout"},
    )
    assert r.status_code == 200
    c = await client.get(
        "/api/v1/security/sessions/check/jti-test-12345",
        headers=headers,
    )
    assert c.status_code == 200
    assert c.json()["revoked"] is True
