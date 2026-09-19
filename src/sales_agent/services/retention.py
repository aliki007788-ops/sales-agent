# ==========================================
# GDPR-style retention cleanup
# ==========================================
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from sales_agent.models.event import Event
from sales_agent.models.lead import Lead


class RetentionService:
    def __init__(
        self,
        session: AsyncSession,
        *,
        events_days: int = 90,
        leads_closed_days: int = 365,
    ) -> None:
        self.session = session
        self.events_days = events_days
        self.leads_closed_days = leads_closed_days

    async def purge_old_events(self, tenant_id: uuid.UUID | None = None) -> int:
        cutoff = datetime.now(tz=timezone.utc) - timedelta(days=self.events_days)
        stmt = delete(Event).where(Event.created_at < cutoff)
        if tenant_id:
            stmt = stmt.where(Event.tenant_id == tenant_id)
        result = await self.session.execute(stmt)
        await self.session.flush()
        return result.rowcount or 0

    async def purge_closed_leads(self, tenant_id: uuid.UUID | None = None) -> int:
        cutoff = datetime.now(tz=timezone.utc) - timedelta(days=self.leads_closed_days)
        stmt = delete(Lead).where(
            Lead.status.in_(("won", "lost", "closed")),
            Lead.updated_at < cutoff,
        )
        if tenant_id:
            stmt = stmt.where(Lead.tenant_id == tenant_id)
        result = await self.session.execute(stmt)
        await self.session.flush()
        return result.rowcount or 0
