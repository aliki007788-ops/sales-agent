# ==========================================
# tests/unit/connectors/test_telegram.py
# ==========================================
from __future__ import annotations

import pytest
import respx
from httpx import Response

from sales_agent.connectors.base import OutboundMessage
from sales_agent.connectors.exceptions import ConnectorAuthError
from sales_agent.connectors.telegram import DEFAULT_BASE_URL, TelegramConnector

TOKEN = "987654:TG-TEST"
BASE = f"{DEFAULT_BASE_URL}/bot{TOKEN}"


@pytest.fixture
def connector():
    return TelegramConnector({"token": TOKEN})


@pytest.mark.asyncio
@respx.mock
async def test_health_check_ok(connector: TelegramConnector) -> None:
    respx.get(f"{BASE}/getMe").mock(
        return_value=Response(200, json={"ok": True, "result": {"id": 1}})
    )
    assert await connector.health_check() is True
    await connector.aclose()


@pytest.mark.asyncio
@respx.mock
async def test_send_message_ok(connector: TelegramConnector) -> None:
    respx.post(f"{BASE}/sendMessage").mock(
        return_value=Response(
            200, json={"ok": True, "result": {"message_id": 99, "text": "hi"}}
        )
    )
    result = await connector.send_message(
        OutboundMessage(chat_id="-100123", text="Hello")
    )
    assert result.external_id == "99"
    await connector.aclose()


@pytest.mark.asyncio
@respx.mock
async def test_send_unauthorized(connector: TelegramConnector) -> None:
    respx.post(f"{BASE}/sendMessage").mock(
        return_value=Response(200, json={"ok": False, "description": "Unauthorized"})
    )
    with pytest.raises(ConnectorAuthError):
        await connector.send_message(OutboundMessage(chat_id="1", text="x"))
    await connector.aclose()
