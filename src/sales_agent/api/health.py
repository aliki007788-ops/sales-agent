# ==========================================
# src/sales_agent/api/health.py
# Version: 1.0 — Phase 1 Core Foundation
# ==========================================
from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter

from sales_agent import __version__
from sales_agent.config import get_settings
from sales_agent.schemas.common import HealthResponse

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    settings = get_settings()
    return HealthResponse(
        status="ok",
        version=__version__,
        environment=settings.environment,
        timestamp=datetime.now(tz=timezone.utc),
    )
