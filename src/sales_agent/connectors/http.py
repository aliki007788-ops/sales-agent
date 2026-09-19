# ==========================================
# src/sales_agent/connectors/http.py
# Version: 1.0 — shared HTTP client + per-host breaker
# ==========================================
from __future__ import annotations

from typing import Any
from urllib.parse import urlparse

import httpx

from sales_agent.connectors.exceptions import (
    ConnectorAuthError,
    ConnectorBadRequest,
    ConnectorError,
    ConnectorRateLimited,
    ConnectorUnavailable,
)
from sales_agent.resilience.breaker import get_breaker


def _host_key(url: str) -> str:
    try:
        return urlparse(url).netloc or "unknown"
    except Exception:
        return "unknown"


class ResilientHttpClient:
    """httpx wrapper with per-host circuit breaker."""

    def __init__(
        self,
        *,
        base_url: str = "",
        timeout: float = 15.0,
        headers: dict[str, str] | None = None,
        breaker_name: str | None = None,
        fail_threshold: int = 5,
        reset_timeout: float = 60.0,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._client = httpx.AsyncClient(
            base_url=self._base_url or None,
            timeout=httpx.Timeout(timeout),
            headers=headers or {},
        )
        key = breaker_name or _host_key(self._base_url or "local")
        self._breaker = get_breaker(
            f"http:{key}",
            fail_threshold=fail_threshold,
            reset_timeout=reset_timeout,
        )

    async def request(
        self,
        method: str,
        path: str,
        *,
        json: dict | None = None,
        data: dict | None = None,
        params: dict | None = None,
        headers: dict | None = None,
    ) -> httpx.Response:
        async def _do() -> httpx.Response:
            try:
                return await self._client.request(
                    method, path, json=json, data=data, params=params, headers=headers
                )
            except httpx.TransportError as exc:
                raise ConnectorUnavailable(f"transport error: {exc}") from exc

        return await self._breaker.call(_do)

    async def get_json(self, path: str, **kwargs: Any) -> dict:
        r = await self.request("GET", path, **kwargs)
        return self._parse(r)

    async def post_json(self, path: str, **kwargs: Any) -> dict:
        r = await self.request("POST", path, **kwargs)
        return self._parse(r)

    def _parse(self, r: httpx.Response) -> dict:
        if r.status_code in (401, 403):
            raise ConnectorAuthError(f"auth failed: {r.status_code}")
        if r.status_code == 429:
            raise ConnectorRateLimited("rate limited")
        if r.status_code >= 500:
            raise ConnectorUnavailable(f"server error: {r.status_code}")
        if r.status_code >= 400:
            raise ConnectorBadRequest(f"bad request: {r.status_code} {r.text[:200]}")
        try:
            data = r.json()
        except ValueError as exc:
            raise ConnectorError(f"non-JSON response: {r.text[:200]}") from exc
        if not isinstance(data, dict):
            return {"result": data}
        # Telegram/Bale style error payload
        if data.get("ok") is False:
            desc = str(data.get("description") or data)
            low = desc.lower()
            if "unauthorized" in low or "token" in low or "auth" in low:
                raise ConnectorAuthError(desc)
            raise ConnectorError(desc)
        return data

    async def aclose(self) -> None:
        await self._client.aclose()
