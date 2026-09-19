# ==========================================
# src/sales_agent/schemas/lead.py
# Version: 1.0 — Phase 4
# ==========================================
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class LeadCreate(BaseModel):
    source: str = Field(min_length=1, max_length=40)
    external_id: str | None = Field(default=None, max_length=120)
    name: str | None = Field(default=None, max_length=120)
    contact: str | None = Field(default=None, max_length=180)
    score: int = Field(default=0, ge=0, le=100)
    status: str = Field(default="new", max_length=20)
    notes: str | None = None
    meta: dict[str, Any] = Field(default_factory=dict)


class LeadUpdate(BaseModel):
    name: str | None = Field(default=None, max_length=120)
    contact: str | None = Field(default=None, max_length=180)
    score: int | None = Field(default=None, ge=0, le=100)
    status: str | None = Field(default=None, max_length=20)
    notes: str | None = None
    meta: dict[str, Any] | None = None


class LeadRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tenant_id: uuid.UUID
    source: str
    external_id: str | None
    name: str | None
    contact: str | None
    score: int
    status: str
    notes: str | None
    meta: dict[str, Any]
    created_at: datetime
    updated_at: datetime
