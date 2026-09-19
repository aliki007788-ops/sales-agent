# ==========================================
# src/sales_agent/connectors/marketplace.py
# Version: 1.0 — Phase 2b
#
# Generic marketplace connector skeleton for
# Torb (ترب) and Emalls (ایمالز).
# These platforms are product-comparison / listing
# oriented; messaging is not the primary API.
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
    ConnectorError,
    ConnectorUnavailable,
)


class MarketplaceConnector(BaseConnector):
    """
    Skeleton for Torb / Emalls style marketplaces.

    credentials:
      - api_key or token
      - base_url (required for real use)
      - channel_name override via subclass
    """

    channel_name = "marketplace"

    def __init__(
        self,
        credentials: dict[str, Any],
        *,
        timeout: float = 15.0,
    ) -> None:
        super().__init__(credentials)
        self._token = credentials.get("token") or credentials.get("api_key") or ""
        self._base = str(credentials.get("base_url") or "").rstrip("/")
        headers: dict[str, str] = {"Accept": "application/json"}
        if self._token:
            headers["Authorization"] = f"Bearer {self._token}"
        self._client = httpx.AsyncClient(
            timeout=httpx.Timeout(timeout),
            headers=headers,
            base_url=self._base or None,
        )

    async def health_check(self) -> bool:
        if not self._base:
            return False
        try:
            r = await self._client.get("/health")
            if r.status_code == 404:
                r = await self._client.get("/")
            return r.status_code < 500
        except Exception:
            return False

    async def send_message(self, message: OutboundMessage) -> SendResult:
        raise ConnectorError(
            f"{self.channel_name}: outbound messaging is not supported. "
            "Use product/search endpoints instead."
        )

    async def get_updates(self, *, offset: int | None = None) -> list[InboundEvent]:
        """Optional product feed as lead-like events if API supports it."""
        if not self._base:
            return []
        path = str(self.credentials.get("search_path") or "/products")
        params: dict[str, Any] = {}
        if offset is not None:
            params["page"] = offset
        try:
            r = await self._client.get(path, params=params or None)
        except httpx.TransportError as exc:
            raise ConnectorUnavailable(f"{self.channel_name} unreachable: {exc}") from exc
        if r.status_code in (401, 403):
            raise ConnectorAuthError(f"{self.channel_name} auth failed")
        if r.status_code >= 400:
            return []
        try:
            data = r.json()
        except ValueError:
            return []
        items = data if isinstance(data, list) else (data.get("results") or data.get("products") or [])
        events: list[InboundEvent] = []
        for item in items if isinstance(items, list) else []:
            if not isinstance(item, dict):
                continue
            pid = str(item.get("id") or item.get("sku") or "")
            title = str(item.get("title") or item.get("name") or "")
            events.append(
                InboundEvent(
                    external_id=pid or title[:40],
                    chat_id=pid,
                    text=title,
                    sender_id=None,
                    raw=item,
                    received_at=datetime.now(tz=timezone.utc),
                )
            )
        return events

    async def aclose(self) -> None:
        await self._client.aclose()


class TorbConnector(MarketplaceConnector):
    channel_name = "torb"


class EmallsConnector(MarketplaceConnector):
    channel_name = "emalls"
