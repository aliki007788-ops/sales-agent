# ==========================================
# src/sales_agent/schemas/tenant.py
# Version: 1.0
# ==========================================
from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class TenantCreate(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    slug: str = Field(pattern=r"^[a-z0-9][a-z0-9\-]{1,58}[a-z0-9]$")
    plan: str = Field(default="free", pattern=r"^(free|pro|business|enterprise)$")


class TenantRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    slug: str
    plan: str
    is_active: bool
    created_at: datetime


class TenantCreated(TenantRead):
    """Returned only once — contains plaintext API key."""

    api_key: str
