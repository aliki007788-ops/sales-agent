# ==========================================
# Minimal Python SDK
# ==========================================
from __future__ import annotations

from typing import Any

import httpx


class SalesAgentClient:
    def __init__(self, base_url: str, api_key: str, *, timeout: float = 30.0) -> None:
        self.base_url = base_url.rstrip("/")
        self._client = httpx.Client(
            base_url=self.base_url,
            headers={"X-API-Key": api_key},
            timeout=timeout,
        )

    def health(self) -> dict[str, Any]:
        r = self._client.get("/health")
        r.raise_for_status()
        return r.json()

    def me(self) -> dict[str, Any]:
        r = self._client.get("/api/v1/tenants/me")
        r.raise_for_status()
        return r.json()

    def create_lead(self, **payload: Any) -> dict[str, Any]:
        r = self._client.post("/api/v1/leads", json=payload)
        r.raise_for_status()
        return r.json()

    def list_leads(self, **params: Any) -> list[dict[str, Any]]:
        r = self._client.get("/api/v1/leads", params=params)
        r.raise_for_status()
        return r.json()

    def set_channel_credentials(
        self, channel: str, credentials: dict[str, Any], webhook_secret: str | None = None
    ) -> dict[str, Any]:
        body: dict[str, Any] = {"credentials": credentials}
        if webhook_secret:
            body["webhook_secret"] = webhook_secret
        r = self._client.post(f"/api/v1/agent/channels/{channel}/credentials", json=body)
        r.raise_for_status()
        return r.json()

    def handle_event(self, **payload: Any) -> dict[str, Any]:
        r = self._client.post("/api/v1/agent/events", json=payload)
        r.raise_for_status()
        return r.json()

    def plans(self) -> list[dict[str, Any]]:
        r = self._client.get("/api/v1/billing/plans")
        r.raise_for_status()
        return r.json()

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> "SalesAgentClient":
        return self

    def __exit__(self, *args: object) -> None:
        self.close()
