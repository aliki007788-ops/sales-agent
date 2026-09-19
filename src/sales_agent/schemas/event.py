# ==========================================
# src/sales_agent/schemas/event.py
# Version: 1.0 — Phase 4
# ==========================================
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class EventCreate(BaseModel):
    channel: str = Field(min_length=1, max_length=40)
    direction: str = Field(pattern=r"^(in|out)$")
    event_type: str = Field(min_length=1, max_length=40)
    payload: dict[str, Any] = Field(default_factory=dict)


class EventRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tenant_id: uuid.UUID
    channel: str
    direction: str
    event_type: str
    payload: dict[str, Any]
    created_at: datetime
