# ==========================================
# src/sales_agent/agent/orchestrator.py
# Version: 1.0 — Phase 3
#
# Simple autonomous loop:
#   event → plan → execute → result
# ==========================================
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable, Awaitable
from enum import Enum

from sales_agent.connectors import (
    BaseConnector,
    InboundEvent,
    OutboundMessage,
    SendResult,
    get_connector,
)
from sales_agent.connectors.exceptions import ConnectorError


class ActionType(str, Enum):
    SEND_MESSAGE = "send_message"
    CREATE_LEAD = "create_lead"
    IGNORE = "ignore"
    LOG = "log"


@dataclass(slots=True)
class AgentAction:
    type: ActionType
    channel: str | None = None
    chat_id: str | None = None
    text: str | None = None
    lead: dict[str, Any] | None = None
    reason: str = ""
    meta: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class AgentResult:
    action: AgentAction
    success: bool
    detail: str = ""
    send_result: SendResult | None = None
    at: datetime = field(default_factory=lambda: datetime.now(tz=timezone.utc))


# Optional LLM planner hook: (event, context) -> AgentAction
PlannerFn = Callable[[InboundEvent, dict[str, Any]], Awaitable[AgentAction]]


class SalesAgent:
    """
    Multi-channel sales agent orchestrator.

    - Holds connector instances per channel
    - Plans next action (rule-based or custom planner)
    - Executes via connectors
    """

    def __init__(
        self,
        tenant_id: str,
        connectors: dict[str, BaseConnector] | None = None,
        *,
        planner: PlannerFn | None = None,
        default_reply: str | None = None,
    ) -> None:
        self.tenant_id = tenant_id
        self.connectors = connectors or {}
        self.planner = planner
        self.default_reply = default_reply or (
            "سلام، پیام شما دریافت شد. به زودی پاسخ می‌دهیم."
        )
        self._history: list[AgentResult] = []

    def register_connector(self, channel: str, connector: BaseConnector) -> None:
        self.connectors[channel] = connector

    def register_from_credentials(
        self, channel: str, credentials: dict[str, Any]
    ) -> None:
        self.connectors[channel] = get_connector(channel, credentials)

    async def handle_event(
        self,
        event: InboundEvent,
        *,
        channel: str,
        context: dict[str, Any] | None = None,
    ) -> AgentResult:
        """Plan + execute for one inbound event."""
        ctx = context or {}
        ctx.setdefault("tenant_id", self.tenant_id)
        ctx.setdefault("channel", channel)

        action = await self._plan(event, ctx)
        result = await self._execute(action, channel=channel)
        self._history.append(result)
        return result

    async def discover_leads(
        self, channel: str, *, limit: int = 20
    ) -> list[InboundEvent]:
        """Pull leads/events from a discovery channel (e.g. divar)."""
        conn = self.connectors.get(channel)
        if conn is None:
            raise ConnectorError(f"No connector registered for {channel}")
        events = await conn.get_updates()
        return events[:limit]

    async def send(
        self, channel: str, chat_id: str, text: str, *, parse_mode: str | None = None
    ) -> AgentResult:
        action = AgentAction(
            type=ActionType.SEND_MESSAGE,
            channel=channel,
            chat_id=chat_id,
            text=text,
            reason="manual_send",
            meta={"parse_mode": parse_mode} if parse_mode else {},
        )
        result = await self._execute(action, channel=channel)
        self._history.append(result)
        return result

    @property
    def history(self) -> list[AgentResult]:
        return list(self._history)

    async def aclose(self) -> None:
        for c in self.connectors.values():
            await c.aclose()

    # --- internals ---

    async def _plan(
        self, event: InboundEvent, context: dict[str, Any]
    ) -> AgentAction:
        if self.planner is not None:
            return await self.planner(event, context)

        # Rule-based default planner (no LLM required for Phase 3)
        text = (event.text or "").strip()
        channel = str(context.get("channel") or "")

        # Discovery channels → create lead
        if channel in ("divar", "torb", "emalls"):
            return AgentAction(
                type=ActionType.CREATE_LEAD,
                channel=channel,
                lead={
                    "external_id": event.external_id,
                    "source": channel,
                    "name": (text.split("\n")[0][:120] if text else None),
                    "notes": text[:2000] if text else None,
                    "meta": event.raw,
                },
                reason="discovery_channel",
            )

        # Empty message → ignore
        if not text:
            return AgentAction(type=ActionType.IGNORE, reason="empty_text")

        # Messaging channels → auto-reply
        if channel in ("bale", "telegram", "eitaa", "rubika") and event.chat_id:
            return AgentAction(
                type=ActionType.SEND_MESSAGE,
                channel=channel,
                chat_id=event.chat_id,
                text=self.default_reply,
                reason="auto_reply",
            )

        return AgentAction(
            type=ActionType.LOG,
            reason="no_rule_matched",
            meta={"event_id": event.external_id, "text": text[:200]},
        )

    async def _execute(
        self, action: AgentAction, *, channel: str | None = None
    ) -> AgentResult:
        ch = action.channel or channel

        if action.type == ActionType.IGNORE:
            return AgentResult(action=action, success=True, detail="ignored")

        if action.type == ActionType.LOG:
            return AgentResult(
                action=action, success=True, detail=f"logged: {action.reason}"
            )

        if action.type == ActionType.CREATE_LEAD:
            # Persistence is Phase 4; for now we acknowledge the lead structure
            return AgentResult(
                action=action,
                success=True,
                detail=f"lead_prepared:{action.lead.get('external_id') if action.lead else ''}",
            )

        if action.type == ActionType.SEND_MESSAGE:
            if not ch or ch not in self.connectors:
                return AgentResult(
                    action=action,
                    success=False,
                    detail=f"no connector for channel={ch}",
                )
            if not action.chat_id or not action.text:
                return AgentResult(
                    action=action, success=False, detail="missing chat_id or text"
                )
            try:
                conn = self.connectors[ch]
                send_result = await conn.send_message(
                    OutboundMessage(
                        chat_id=action.chat_id,
                        text=action.text,
                        parse_mode=(action.meta or {}).get("parse_mode"),
                    )
                )
                return AgentResult(
                    action=action,
                    success=True,
                    detail=f"sent:{send_result.external_id}",
                    send_result=send_result,
                )
            except ConnectorError as exc:
                return AgentResult(action=action, success=False, detail=str(exc))

        return AgentResult(action=action, success=False, detail="unknown_action")
