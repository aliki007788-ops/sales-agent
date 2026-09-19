# ==========================================
# src/sales_agent/api/v1/tenants.py
# Version: 1.0 — Phase 1 Core Foundation
# ==========================================
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from sales_agent.api.deps import get_current_tenant
from sales_agent.db.session import get_session
from sales_agent.models.tenant import Tenant
from sales_agent.schemas.tenant import TenantCreate, TenantCreated, TenantRead
from sales_agent.security.api_key import generate_api_key

router = APIRouter(prefix="/tenants", tags=["tenants"])


@router.post(
    "",
    response_model=TenantCreated,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new tenant and return its API key (once).",
)
async def create_tenant(
    payload: TenantCreate,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> TenantCreated:
    plaintext, prefix, hashed = generate_api_key()

    tenant = Tenant(
        name=payload.name,
        slug=payload.slug,
        plan=payload.plan,
        api_key_prefix=prefix,
        api_key_hash=hashed,
    )
    session.add(tenant)
    try:
        await session.flush()
    except IntegrityError as exc:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Tenant slug already exists",
        ) from exc

    await session.refresh(tenant)
    return TenantCreated(
        id=tenant.id,
        name=tenant.name,
        slug=tenant.slug,
        plan=tenant.plan,
        is_active=tenant.is_active,
        created_at=tenant.created_at,
        api_key=plaintext,
    )


@router.get(
    "/me",
    response_model=TenantRead,
    summary="Return the authenticated tenant.",
)
async def read_me(
    tenant: Annotated[Tenant, Depends(get_current_tenant)],
) -> TenantRead:
    return TenantRead.model_validate(tenant)
