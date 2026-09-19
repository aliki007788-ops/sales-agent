# ==========================================
# src/sales_agent/api/v1/leads.py
# Version: 1.0 — Phase 4
# ==========================================
from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from sales_agent.api.deps import get_current_tenant
from sales_agent.db.session import get_session
from sales_agent.models.tenant import Tenant
from sales_agent.schemas.lead import LeadCreate, LeadRead, LeadUpdate
from sales_agent.services.leads import LeadService

router = APIRouter(prefix="/leads", tags=["leads"])


@router.post("", response_model=LeadRead, status_code=status.HTTP_201_CREATED)
async def create_lead(
    payload: LeadCreate,
    tenant: Annotated[Tenant, Depends(get_current_tenant)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> LeadRead:
    svc = LeadService(session, tenant.id)
    lead = await svc.create(payload)
    return LeadRead.model_validate(lead)


@router.get("", response_model=list[LeadRead])
async def list_leads(
    tenant: Annotated[Tenant, Depends(get_current_tenant)],
    session: Annotated[AsyncSession, Depends(get_session)],
    source: str | None = None,
    status_filter: Annotated[str | None, Query(alias="status")] = None,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> list[LeadRead]:
    svc = LeadService(session, tenant.id)
    rows = await svc.list(source=source, status=status_filter, limit=limit, offset=offset)
    return [LeadRead.model_validate(r) for r in rows]


@router.get("/{lead_id}", response_model=LeadRead)
async def get_lead(
    lead_id: uuid.UUID,
    tenant: Annotated[Tenant, Depends(get_current_tenant)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> LeadRead:
    svc = LeadService(session, tenant.id)
    lead = await svc.get(lead_id)
    if lead is None:
        raise HTTPException(status_code=404, detail="Lead not found")
    return LeadRead.model_validate(lead)


@router.patch("/{lead_id}", response_model=LeadRead)
async def update_lead(
    lead_id: uuid.UUID,
    payload: LeadUpdate,
    tenant: Annotated[Tenant, Depends(get_current_tenant)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> LeadRead:
    svc = LeadService(session, tenant.id)
    lead = await svc.update(lead_id, payload)
    if lead is None:
        raise HTTPException(status_code=404, detail="Lead not found")
    return LeadRead.model_validate(lead)
