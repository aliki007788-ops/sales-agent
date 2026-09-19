# ==========================================
# src/sales_agent/connectors/eitaa.py
# Version: 1.0 — Phase 2b
#
# Eitaa (ایتا) — via Eitaayar-style HTTP API
# Docs pattern: https://eitaayar.ir/api/{token}/sendMessage
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

DEFAULT_BASE_URL = "https://eitaayar.ir/api"


class EitaaConnector(BaseConnector):
    """Connector for Eitaa messenger (Eitaayar API style)."""

    channel_name = "eitaa"

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
            raise ConnectorAuthError("Eitaa token is required")
        self._token = str(token)
        self._base = (base_url or DEFAULT_BASE_URL).rstrip("/")
        self._client = httpx.AsyncClient(timeout=httpx.Timeout(timeout))

    def _url(self, method: str) -> str:
        return f"{self._base}/{self._token}/{method}"

    async def health_check(self) -> bool:
        # Eitaayar has no universal getMe; try a lightweight call pattern
        try:
            r = await self._client.get(self._url("getMe"))
            if r.status_code in (401, 403):
                return False
            if r.status_code == 404:
                # some deployments don't expose getMe — treat token presence as ok
                return True
            data = r.json() if r.headers.get("content-type", "").startswith("application/json") else {}
            return bool(data.get("ok", r.status_code < 400))
        except Exception:
            return False

    async def send_message(self, message: OutboundMessage) -> SendResult:
        # Eitaayar: chat_id can be channel username or numeric id
        payload = {
            "chat_id": message.chat_id,
            "text": message.text,
        }
        if message.parse_mode:
            payload["parse_mode"] = message.parse_mode

        try:
            r = await self._client.post(self._url("sendMessage"), data=payload)
        except httpx.TransportError as exc:
            raise ConnectorUnavailable(f"Eitaa unreachable: {exc}") from exc

        self._raise_for_status(r)
        try:
            data = r.json()
        except ValueError as exc:
            raise ConnectorError(f"Eitaa non-JSON: {r.text[:200]}") from exc

        result = data.get("result") or data
        ext_id = str(result.get("message_id") or result.get("id") or "")
        return SendResult(
            external_id=ext_id,
            sent_at=datetime.now(tz=timezone.utc),
            raw=result if isinstance(result, dict) else {"raw": result},
        )

    async def get_updates(self, *, offset: int | None = None) -> list[InboundEvent]:
        # Eitaayar primarily pushes via webhook; polling is limited
        return []

    async def aclose(self) -> None:
        await self._client.aclose()

    def _raise_for_status(self, r: httpx.Response) -> None:
        if r.status_code in (401, 403):
            raise ConnectorAuthError(f"Eitaa auth failed: {r.status_code}")
        if r.status_code == 429:
            raise ConnectorRateLimited("Eitaa rate limit")
        if r.status_code >= 500:
            raise ConnectorUnavailable(f"Eitaa server error: {r.status_code}")
        if r.status_code >= 400:
            raise ConnectorBadRequest(f"Eitaa error {r.status_code}: {r.text[:200]}")
