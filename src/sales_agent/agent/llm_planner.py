# ==========================================
# Optional LLM-backed planner
# ==========================================
from __future__ import annotations

import json
from typing import Any

from sales_agent.agent.orchestrator import ActionType, AgentAction
from sales_agent.ai.llm import LLMClient
from sales_agent.connectors.base import InboundEvent


async def llm_plan(
    event: InboundEvent,
    context: dict[str, Any],
    *,
    client: LLMClient | None = None,
) -> AgentAction:
    llm = client or LLMClient()
    channel = str(context.get("channel") or "")
    system = (
        "You are a sales agent planner. Reply ONLY with JSON: "
        '{"action":"send_message|create_lead|ignore","text":"...","reason":"..."}'
    )
    user = (
        f"channel={channel}\n"
        f"chat_id={event.chat_id}\n"
        f"text={event.text!r}\n"
        f"Decide the next action."
    )
    try:
        resp = await llm.complete(system, user, json_mode=True)
        data = json.loads(resp.text)
    except Exception:
        return AgentAction(type=ActionType.IGNORE, reason="llm_parse_failed")
    finally:
        if client is None:
            await llm.aclose()

    action = str(data.get("action") or "ignore")
    if action == "send_message":
        return AgentAction(
            type=ActionType.SEND_MESSAGE,
            channel=channel,
            chat_id=event.chat_id,
            text=str(data.get("text") or "سلام"),
            reason=str(data.get("reason") or "llm"),
        )
    if action == "create_lead":
        return AgentAction(
            type=ActionType.CREATE_LEAD,
            channel=channel,
            lead={
                "source": channel,
                "external_id": event.external_id,
                "name": (event.text or "")[:120],
                "notes": event.text,
                "meta": event.raw,
            },
            reason=str(data.get("reason") or "llm"),
        )
    return AgentAction(type=ActionType.IGNORE, reason=str(data.get("reason") or "llm"))
