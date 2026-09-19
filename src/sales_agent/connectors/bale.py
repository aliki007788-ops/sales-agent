# ==========================================
# Bale connector — ResilientHttpClient
# ==========================================
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sales_agent.connectors.base import (
    BaseConnector,
    InboundEvent,
    OutboundMessage,
    SendResult,
)
from sales_agent.connectors.exceptions import ConnectorAuthError, ConnectorError
from sales_agent.connectors.http import ResilientHttpClient

DEFAULT_BASE_URL = "https://tapi.bale.ai"


class BaleConnector(BaseConnector):
    channel_name = "bale"

    def __init__(
        self,
        credentials: dict[str, Any],
        *,
        base_url: str | None = None,
        timeout: float = 15.0,
    ) -> None:
        super().__init__(credentials)
        token = credentials.get("token") or credentials.get("bot_token")
        if not token:
            raise ConnectorAuthError("Bale token is required in credentials")
        self._token = str(token)
        base = (base_url or DEFAULT_BASE_URL).rstrip("/")
        self._http = ResilientHttpClient(
            base_url=f"{base}/bot{self._token}",
            timeout=timeout,
            breaker_name="bale",
        )

    async def health_check(self) -> bool:
        try:
            data = await self._http.get_json("/getMe")
            return bool(data.get("ok"))
        except ConnectorError:
            return False

    async def send_message(self, message: OutboundMessage) -> SendResult:
        body: dict[str, Any] = {"chat_id": message.chat_id, "text": message.text}
        if message.parse_mode:
            body["parse_mode"] = message.parse_mode
        data = await self._http.post_json("/sendMessage", json=body)
        result = data.get("result") or {}
        return SendResult(
            external_id=str(result.get("message_id", "")),
            sent_at=datetime.now(tz=timezone.utc),
            raw=result,
        )

    async def get_updates(self, *, offset: int | None = None) -> list[InboundEvent]:
        params: dict[str, Any] = {"timeout": 0}
        if offset is not None:
            params["offset"] = offset
        data = await self._http.get_json("/getUpdates", params=params)
        events: list[InboundEvent] = []
        for item in data.get("result") or []:
            msg = item.get("message") or item.get("edited_message") or {}
            chat = msg.get("chat") or {}
            from_user = msg.get("from") or {}
            events.append(
                InboundEvent(
                    external_id=str(item.get("update_id", "")),
                    chat_id=str(chat.get("id", "")),
                    text=msg.get("text"),
                    sender_id=str(from_user.get("id", "")) if from_user else None,
                    raw=item,
                )
            )
        return events

    async def aclose(self) -> None:
        await self._http.aclose()
