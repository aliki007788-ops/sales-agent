# ==========================================
# src/sales_agent/schemas/common.py
# Version: 1.0
# ==========================================
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class HealthResponse(BaseModel):
    status: str
    version: str
    environment: str
    timestamp: datetime
