# ==========================================
# src/sales_agent/schemas/agent.py
# Version: 1.0 — Phase 4
# ==========================================
from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class InboundEventPayload(BaseModel):
    """Webhook / API payload for an inbound channel event."""

    channel: str = Field(min_length=1, max_length=40)
    external_id: str = Field(default="", max_length=120)
    chat_id: str = Field(default="", max_length=120)
    text: str | None = None
    sender_id: str | None = None
    raw: dict[str, Any] = Field(default_factory=dict)


class HandleEventResponse(BaseModel):
    success: bool
    action_type: str
    detail: str
    lead_id: str | None = None
    message_external_id: str | None = None


class CampaignStartRequest(BaseModel):
    """Simple campaign: discover leads from a channel and process them."""

    channel: str = Field(min_length=1, max_length=40)
    limit: int = Field(default=10, ge=1, le=100)
    auto_process: bool = True


class CampaignStartResponse(BaseModel):
    channel: str
    discovered: int
    processed: int
    results: list[HandleEventResponse]
