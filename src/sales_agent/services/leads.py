# ==========================================
# src/sales_agent/services/leads.py
# Version: 1.0 — Phase 4
# ==========================================
from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from sales_agent.models.lead import Lead
from sales_agent.schemas.lead import LeadCreate, LeadUpdate


class LeadService:
    def __init__(self, session: AsyncSession, tenant_id: uuid.UUID) -> None:
        self.session = session
        self.tenant_id = tenant_id

    async def create(self, data: LeadCreate) -> Lead:
        lead = Lead(
            tenant_id=self.tenant_id,
            source=data.source,
            external_id=data.external_id,
            name=data.name,
            contact=data.contact,
            score=data.score,
            status=data.status,
            notes=data.notes,
            meta=data.meta or {},
        )
        self.session.add(lead)
        await self.session.flush()
        await self.session.refresh(lead)
        return lead

    async def create_from_dict(self, payload: dict[str, Any]) -> Lead:
        data = LeadCreate(
            source=str(payload.get("source") or "unknown"),
            external_id=payload.get("external_id"),
            name=payload.get("name"),
            contact=payload.get("contact"),
            score=int(payload.get("score") or 0),
            status=str(payload.get("status") or "new"),
            notes=payload.get("notes"),
            meta=payload.get("meta") or {},
        )
        return await self.create(data)

    async def get(self, lead_id: uuid.UUID) -> Lead | None:
        stmt = select(Lead).where(
            Lead.id == lead_id,
            Lead.tenant_id == self.tenant_id,
        )
        return (await self.session.execute(stmt)).scalar_one_or_none()

    async def list(
        self,
        *,
        source: str | None = None,
        status: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[Lead]:
        stmt = select(Lead).where(Lead.tenant_id == self.tenant_id)
        if source:
            stmt = stmt.where(Lead.source == source)
        if status:
            stmt = stmt.where(Lead.status == status)
        stmt = stmt.order_by(Lead.created_at.desc()).offset(offset).limit(limit)
        return list((await self.session.execute(stmt)).scalars().all())

    async def update(self, lead_id: uuid.UUID, data: LeadUpdate) -> Lead | None:
        lead = await self.get(lead_id)
        if lead is None:
            return None
        for field, value in data.model_dump(exclude_unset=True).items():
            setattr(lead, field, value)
        await self.session.flush()
        await self.session.refresh(lead)
        return lead

    async def find_by_external(
        self, source: str, external_id: str
    ) -> Lead | None:
        stmt = select(Lead).where(
            Lead.tenant_id == self.tenant_id,
            Lead.source == source,
            Lead.external_id == external_id,
        )
        return (await self.session.execute(stmt)).scalar_one_or_none()
