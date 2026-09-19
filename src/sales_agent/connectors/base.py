# ==========================================
# src/sales_agent/connectors/base.py
# Version: 1.0 — Phase 2
# ==========================================
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


@dataclass(slots=True)
class OutboundMessage:
    """A message the agent wants to send."""

    chat_id: str
    text: str
    parse_mode: str | None = None  # e.g. "Markdown", "HTML"
    meta: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class SendResult:
    """Result of a successful send."""

    external_id: str
    sent_at: datetime
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class InboundEvent:
    """A normalized inbound event from any channel."""

    external_id: str
    chat_id: str
    text: str | None
    sender_id: str | None
    raw: dict[str, Any] = field(default_factory=dict)
    received_at: datetime = field(
        default_factory=lambda: datetime.now(tz=timezone.utc)
    )


class BaseConnector(ABC):
    """Abstract base for all channel connectors."""

    channel_name: str = "base"

    def __init__(self, credentials: dict[str, Any]) -> None:
        self.credentials = credentials

    @abstractmethod
    async def health_check(self) -> bool:
        """Return True if the connector can talk to the upstream API."""

    @abstractmethod
    async def send_message(self, message: OutboundMessage) -> SendResult:
        """Send a text message and return a SendResult."""

    @abstractmethod
    async def get_updates(self, *, offset: int | None = None) -> list[InboundEvent]:
        """Poll for new inbound events (if supported)."""

    async def aclose(self) -> None:
        """Release resources (HTTP clients, etc.). Override if needed."""
        return None
