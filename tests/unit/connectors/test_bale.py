# ==========================================
# tests/unit/connectors/test_bale.py
# ==========================================
from __future__ import annotations

import pytest
import respx
from httpx import Response

from sales_agent.connectors.bale import BaleConnector, DEFAULT_BASE_URL
from sales_agent.connectors.base import OutboundMessage
from sales_agent.connectors.exceptions import (
    ConnectorAuthError,
    ConnectorUnavailable,
)


TOKEN = "123456:TEST-TOKEN"
BASE = f"{DEFAULT_BASE_URL}/bot{TOKEN}"


@pytest.fixture
def connector():
    return BaleConnector({"token": TOKEN})


@pytest.mark.asyncio
@respx.mock
async def test_health_check_ok(connector: BaleConnector) -> None:
    respx.get(f"{BASE}/getMe").mock(
        return_value=Response(200, json={"ok": True, "result": {"id": 1, "username": "bot"}})
    )
    assert await connector.health_check() is True
    await connector.aclose()


@pytest.mark.asyncio
@respx.mock
async def test_health_check_auth_fail(connector: BaleConnector) -> None:
    respx.get(f"{BASE}/getMe").mock(return_value=Response(401, json={"ok": False}))
    assert await connector.health_check() is False
    await connector.aclose()


@pytest.mark.asyncio
@respx.mock
async def test_send_message_ok(connector: BaleConnector) -> None:
    respx.post(f"{BASE}/sendMessage").mock(
        return_value=Response(
            200,
            json={"ok": True, "result": {"message_id": 42, "text": "hi"}},
        )
    )
    result = await connector.send_message(
        OutboundMessage(chat_id="999", text="سلام تست")
    )
    assert result.external_id == "42"
    assert result.sent_at is not None
    await connector.aclose()


@pytest.mark.asyncio
@respx.mock
async def test_send_message_auth_error(connector: BaleConnector) -> None:
    respx.post(f"{BASE}/sendMessage").mock(return_value=Response(403, text="Forbidden"))
    with pytest.raises(ConnectorAuthError):
        await connector.send_message(OutboundMessage(chat_id="1", text="x"))
    await connector.aclose()


@pytest.mark.asyncio
@respx.mock
async def test_get_updates(connector: BaleConnector) -> None:
    respx.get(f"{BASE}/getUpdates").mock(
        return_value=Response(
            200,
            json={
                "ok": True,
                "result": [
                    {
                        "update_id": 10,
                        "message": {
                            "message_id": 1,
                            "text": "hello",
                            "chat": {"id": 555},
                            "from": {"id": 777},
                        },
                    }
                ],
            },
        )
    )
    events = await connector.get_updates()
    assert len(events) == 1
    assert events[0].chat_id == "555"
    assert events[0].text == "hello"
    assert events[0].sender_id == "777"
    await connector.aclose()


@pytest.mark.asyncio
async def test_missing_token() -> None:
    with pytest.raises(ConnectorAuthError):
        BaleConnector({})
