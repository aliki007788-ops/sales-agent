# ==========================================
# src/sales_agent/connectors/divar.py
# Version: 1.0 — Phase 2b
#
# Divar (دیوار) — lead discovery (search listings).
# Messaging private users is restricted; this connector
# focuses on fetching new posts as leads.
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
    ConnectorUnavailable,
)

# Public search endpoint pattern (may change; override via credentials)
DEFAULT_SEARCH_URL = "https://api.divar.ir/v8/web-search/{city}/{category}"


class DivarConnector(BaseConnector):
    """
    Divar connector for lead discovery.

    credentials:
      - city: e.g. "tehran"
      - category: e.g. "electronic-devices" or empty for root
      - token (optional): if Divar adds authenticated APIs later
    """

    channel_name = "divar"

    def __init__(
        self,
        credentials: dict[str, Any],
        *,
        timeout: float = 20.0,
    ) -> None:
        super().__init__(credentials)
        self._city = str(credentials.get("city") or "tehran")
        self._category = str(credentials.get("category") or "")
        self._token = credentials.get("token")
        headers: dict[str, str] = {
            "Accept": "application/json",
            "User-Agent": "SalesAgent/0.1 (lead-discovery)",
        }
        if self._token:
            headers["Authorization"] = f"Bearer {self._token}"
        self._client = httpx.AsyncClient(
            timeout=httpx.Timeout(timeout),
            headers=headers,
        )

    async def health_check(self) -> bool:
        try:
            # lightweight probe — homepage API or search root
            r = await self._client.get("https://api.divar.ir/v8/app-config")
            return r.status_code < 500
        except Exception:
            return False

    async def send_message(self, message: OutboundMessage) -> SendResult:
        # Divar does not offer a general bot sendMessage for arbitrary users.
        raise ConnectorError(
            "Divar does not support outbound bot messaging. "
            "Use Divar for lead discovery (get_updates / search) only."
        )

    async def get_updates(self, *, offset: int | None = None) -> list[InboundEvent]:
        """Fetch recent listings and map them to InboundEvent (as leads)."""
        city = self._city
        category = self._category or ""
        url = DEFAULT_SEARCH_URL.format(city=city, category=category).rstrip("/")
        if not category:
            url = f"https://api.divar.ir/v8/web-search/{city}"

        params: dict[str, Any] = {}
        if offset:
            params["page"] = offset

        try:
            r = await self._client.get(url, params=params or None)
        except httpx.TransportError as exc:
            raise ConnectorUnavailable(f"Divar unreachable: {exc}") from exc

        if r.status_code in (401, 403):
            raise ConnectorAuthError("Divar auth/blocked")
        if r.status_code >= 400:
            raise ConnectorBadRequest(f"Divar search error: {r.status_code}")

        try:
            data = r.json()
        except ValueError as exc:
            raise ConnectorError("Divar returned non-JSON") from exc

        # web-search response shape varies; try common keys
        posts = (
            data.get("web_widgets")
            or data.get("list_widgets")
            or data.get("widget_list")
            or data.get("posts")
            or []
        )

        events: list[InboundEvent] = []
        for item in posts if isinstance(posts, list) else []:
            # widgets often wrap data
            widget_data = item.get("data") if isinstance(item, dict) else None
            post = widget_data or item if isinstance(item, dict) else {}
            if not isinstance(post, dict):
                continue
            token = str(post.get("token") or post.get("id") or "")
            title = post.get("title") or post.get("name") or ""
            desc = post.get("description") or post.get("subtitle") or ""
            if not token and not title:
                continue
            events.append(
                InboundEvent(
                    external_id=token or title[:40],
                    chat_id=token,  # use post token as reference
                    text=f"{title}\n{desc}".strip(),
                    sender_id=None,
                    raw=post,
                    received_at=datetime.now(tz=timezone.utc),
                )
            )
        return events

    async def aclose(self) -> None:
        await self._client.aclose()
