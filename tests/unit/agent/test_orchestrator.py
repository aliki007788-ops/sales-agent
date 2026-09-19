# ==========================================
# tests/unit/agent/test_orchestrator.py
# ==========================================
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import pytest
import respx
from httpx import Response

from sales_agent.agent.orchestrator import ActionType, SalesAgent
from sales_agent.connectors.bale import BaleConnector, DEFAULT_BASE_URL
from sales_agent.connectors.base import InboundEvent
from sales_agent.connectors.divar import DivarConnector


TOKEN = "111:TEST"
BASE = f"{DEFAULT_BASE_URL}/bot{TOKEN}"


@pytest.fixture
def agent() -> SalesAgent:
    a = SalesAgent(tenant_id="t-1", default_reply="پاسخ خودکار")
    a.register_connector("bale", BaleConnector({"token": TOKEN}))
    a.register_connector("divar", DivarConnector({"city": "tehran"}))
    return a


@pytest.mark.asyncio
@respx.mock
async def test_auto_reply_on_bale(agent: SalesAgent) -> None:
    respx.post(f"{BASE}/sendMessage").mock(
        return_value=Response(
            200, json={"ok": True, "result": {"message_id": 7}}
        )
    )
    event = InboundEvent(
        external_id="1",
        chat_id="999",
        text="سلام",
        sender_id="u1",
    )
    result = await agent.handle_event(event, channel="bale")
    assert result.success is True
    assert result.action.type == ActionType.SEND_MESSAGE
    assert result.send_result is not None
    assert result.send_result.external_id == "7"
    await agent.aclose()


@pytest.mark.asyncio
async def test_divar_creates_lead_action(agent: SalesAgent) -> None:
    event = InboundEvent(
        external_id="post-1",
        chat_id="post-1",
        text="آیفون ۱۳\nفروشی",
        sender_id=None,
        raw={"token": "post-1"},
    )
    result = await agent.handle_event(event, channel="divar")
    assert result.success is True
    assert result.action.type == ActionType.CREATE_LEAD
    assert result.action.lead is not None
    assert result.action.lead["source"] == "divar"
    await agent.aclose()


@pytest.mark.asyncio
async def test_empty_message_ignored(agent: SalesAgent) -> None:
    event = InboundEvent(
        external_id="2", chat_id="1", text="  ", sender_id=None
    )
    result = await agent.handle_event(event, channel="bale")
    assert result.success is True
    assert result.action.type == ActionType.IGNORE
    await agent.aclose()


@pytest.mark.asyncio
@respx.mock
async def test_manual_send(agent: SalesAgent) -> None:
    respx.post(f"{BASE}/sendMessage").mock(
        return_value=Response(
            200, json={"ok": True, "result": {"message_id": 3}}
        )
    )
    result = await agent.send("bale", "chat-9", "پیام دستی")
    assert result.success is True
    assert result.action.type == ActionType.SEND_MESSAGE
    await agent.aclose()


@pytest.mark.asyncio
async def test_custom_planner() -> None:
    async def my_planner(event: InboundEvent, ctx: dict[str, Any]):
        from sales_agent.agent.orchestrator import AgentAction

        return AgentAction(
            type=ActionType.LOG,
            reason="custom",
            meta={"text": event.text},
        )

    agent = SalesAgent(tenant_id="t-2", planner=my_planner)
    event = InboundEvent(external_id="x", chat_id="1", text="hi", sender_id=None)
    result = await agent.handle_event(event, channel="bale")
    assert result.action.type == ActionType.LOG
    assert result.action.reason == "custom"
    await agent.aclose()
