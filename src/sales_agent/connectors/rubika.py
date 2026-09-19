# ==========================================
# src/sales_agent/connectors/rubika.py
# Version: 1.0 — Phase 2b
#
# Rubika (روبیکا) — best-effort Bot API style.
# Public official docs are limited; many bots use
# community endpoints. Override base_url if needed.
# ==========================================
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import httpx

from sales_agent.connectors.base import (
    BaseConnector,
    InboundEvent,
    OutboundMessage,
    SendResult,
)
from sales_agent.connectors.exceptions import (
    ConnectorAuthError,
    ConnectorBadRequest,
    ConnectorError,
    ConnectorRateLimited,
    ConnectorUnavailable,
)

# Common community / bot gateway patterns (override via credentials["base_url"])
DEFAULT_BASE_URL = "https://botapi.rubika.ir/v3"


class RubikaConnector(BaseConnector):
    """Connector for Rubika messenger bots."""

    channel_name = "rubika"

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
            raise ConnectorAuthError("Rubika token is required")
        self._token = str(token)
        self._base = (base_url or credentials.get("base_url") or DEFAULT_BASE_URL).rstrip("/")
        self._client = httpx.AsyncClient(
            timeout=httpx.Timeout(timeout),
            headers={"Authorization": f"Bearer {self._token}"},
        )

    async def health_check(self) -> bool:
        try:
            r = await self._client.get(f"{self._base}/getMe")
            if r.status_code in (401, 403):
                return False
            if r.status_code >= 500:
                return False
            return r.status_code < 400
        except Exception:
            return False

    async def send_message(self, message: OutboundMessage) -> SendResult:
        body: dict[str, Any] = {
            "chat_id": message.chat_id,
            "text": message.text,
        }
        if message.parse_mode:
            body["parse_mode"] = message.parse_mode

        try:
            r = await self._client.post(f"{self._base}/sendMessage", json=body)
        except httpx.TransportError as exc:
            raise ConnectorUnavailable(f"Rubika unreachable: {exc}") from exc

        self._raise_for_status(r)
        try:
            data = r.json()
        except ValueError as exc:
            raise ConnectorError(f"Rubika non-JSON: {r.text[:200]}") from exc

        result = data.get("result") or data.get("data") or data
        ext_id = str(
            (result.get("message_id") if isinstance(result, dict) else None)
            or (result.get("id") if isinstance(result, dict) else None)
            or ""
        )
        return SendResult(
            external_id=ext_id,
            sent_at=datetime.now(tz=timezone.utc),
            raw=result if isinstance(result, dict) else {"raw": result},
        )

    async def get_updates(self, *, offset: int | None = None) -> list[InboundEvent]:
        params: dict[str, Any] = {}
        if offset is not None:
            params["offset"] = offset
        try:
            r = await self._client.get(f"{self._base}/getUpdates", params=params or None)
        except httpx.TransportError as exc:
            raise ConnectorUnavailable(f"Rubika unreachable: {exc}") from exc

        if r.status_code >= 400:
            return []

        try:
            data = r.json()
        except ValueError:
            return []

        items = data.get("result") or data.get("data") or []
        events: list[InboundEvent] = []
        for item in items if isinstance(items, list) else []:
            msg = item.get("message") or item if isinstance(item, dict) else {}
            if not isinstance(msg, dict):
                continue
            chat = msg.get("chat") or {}
            from_user = msg.get("from") or msg.get("sender") or {}
            events.append(
                InboundEvent(
                    external_id=str(item.get("update_id") or item.get("id") or ""),
                    chat_id=str(chat.get("id") or msg.get("chat_id") or ""),
                    text=msg.get("text"),
                    sender_id=str(from_user.get("id") or "") or None,
                    raw=item,
                )
            )
        return events

    async def aclose(self) -> None:
        await self._client.aclose()

    def _raise_for_status(self, r: httpx.Response) -> None:
        if r.status_code in (401, 403):
            raise ConnectorAuthError(f"Rubika auth failed: {r.status_code}")
        if r.status_code == 429:
            raise ConnectorRateLimited("Rubika rate limit")
        if r.status_code >= 500:
            raise ConnectorUnavailable(f"Rubika server error: {r.status_code}")
        if r.status_code >= 400:
            raise ConnectorBadRequest(f"Rubika error {r.status_code}: {r.text[:200]}")
