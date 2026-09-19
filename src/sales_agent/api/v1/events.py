# ==========================================
# src/sales_agent/api/v1/events.py
# Version: 1.0 — Phase 4
# ==========================================
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from sales_agent.api.deps import get_current_tenant
from sales_agent.db.session import get_session
from sales_agent.models.tenant import Tenant
from sales_agent.schemas.event import EventCreate, EventRead
from sales_agent.services.events import EventService

router = APIRouter(prefix="/events", tags=["events"])


@router.post("", response_model=EventRead, status_code=status.HTTP_201_CREATED)
async def create_event(
    payload: EventCreate,
    tenant: Annotated[Tenant, Depends(get_current_tenant)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> EventRead:
    svc = EventService(session, tenant.id)
    event = await svc.create(payload)
    return EventRead.model_validate(event)


@router.get("", response_model=list[EventRead])
async def list_events(
    tenant: Annotated[Tenant, Depends(get_current_tenant)],
    session: Annotated[AsyncSession, Depends(get_session)],
    channel: str | None = None,
    direction: str | None = None,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> list[EventRead]:
    svc = EventService(session, tenant.id)
    rows = await svc.list(channel=channel, direction=direction, limit=limit, offset=offset)
    return [EventRead.model_validate(r) for r in rows]
