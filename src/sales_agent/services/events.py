# ==========================================
# src/sales_agent/services/events.py
# Version: 1.0 — Phase 4
# ==========================================
from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from sales_agent.models.event import Event
from sales_agent.schemas.event import EventCreate


class EventService:
    def __init__(self, session: AsyncSession, tenant_id: uuid.UUID) -> None:
        self.session = session
        self.tenant_id = tenant_id

    async def create(self, data: EventCreate) -> Event:
        event = Event(
            tenant_id=self.tenant_id,
            channel=data.channel,
            direction=data.direction,
            event_type=data.event_type,
            payload=data.payload or {},
        )
        self.session.add(event)
        await self.session.flush()
        await self.session.refresh(event)
        return event

    async def log_inbound(
        self,
        channel: str,
        payload: dict[str, Any],
        *,
        event_type: str = "message",
    ) -> Event:
        return await self.create(
            EventCreate(
                channel=channel,
                direction="in",
                event_type=event_type,
                payload=payload,
            )
        )

    async def log_outbound(
        self,
        channel: str,
        payload: dict[str, Any],
        *,
        event_type: str = "message",
    ) -> Event:
        return await self.create(
            EventCreate(
                channel=channel,
                direction="out",
                event_type=event_type,
                payload=payload,
            )
        )

    async def list(
        self,
        *,
        channel: str | None = None,
        direction: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[Event]:
        stmt = select(Event).where(Event.tenant_id == self.tenant_id)
        if channel:
            stmt = stmt.where(Event.channel == channel)
        if direction:
            stmt = stmt.where(Event.direction == direction)
        stmt = stmt.order_by(Event.created_at.desc()).offset(offset).limit(limit)
        return list((await self.session.execute(stmt)).scalars().all())
