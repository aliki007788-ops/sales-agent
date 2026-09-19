# ==========================================
# Team / membership API (basic RBAC)
# ==========================================
from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from sales_agent.api.deps import get_current_tenant
from sales_agent.db.session import get_session
from sales_agent.models.membership import ROLES, Membership
from sales_agent.models.tenant import Tenant

router = APIRouter(prefix="/team", tags=["team"])


class MemberCreate(BaseModel):
    email: str = Field(min_length=3, max_length=180)
    role: str = Field(default="agent")
    display_name: str | None = None


class MemberRead(BaseModel):
    id: uuid.UUID
    email: str
    role: str
    display_name: str | None

    class Config:
        from_attributes = True


@router.post("", response_model=MemberRead, status_code=status.HTTP_201_CREATED)
async def add_member(
    body: MemberCreate,
    tenant: Annotated[Tenant, Depends(get_current_tenant)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> Membership:
    if body.role not in ROLES:
        raise HTTPException(400, detail=f"role must be one of {ROLES}")
    m = Membership(
        tenant_id=tenant.id,
        email=body.email.lower(),
        role=body.role,
        display_name=body.display_name,
    )
    session.add(m)
    try:
        await session.flush()
    except Exception as exc:
        raise HTTPException(409, detail="Member already exists") from exc
    await session.refresh(m)
    return m


@router.get("", response_model=list[MemberRead])
async def list_members(
    tenant: Annotated[Tenant, Depends(get_current_tenant)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> list[Membership]:
    rows = (
        await session.execute(
            select(Membership)
            .where(Membership.tenant_id == tenant.id)
            .order_by(Membership.created_at)
        )
    ).scalars().all()
    return list(rows)
