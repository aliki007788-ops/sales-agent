# ==========================================
# Security API: TOTP + session revoke
# ==========================================
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from sales_agent.api.deps import get_current_tenant
from sales_agent.db.session import get_session
from sales_agent.models.tenant import Tenant
from sales_agent.services.sessions import SessionDenyService
from sales_agent.services.totp_service import TotpService

router = APIRouter(prefix="/security", tags=["security"])


class TotpEnrollRequest(BaseModel):
    email: str = Field(min_length=3, max_length=180)


class TotpVerifyRequest(BaseModel):
    email: str
    code: str = Field(min_length=6, max_length=8)


class RevokeSessionRequest(BaseModel):
    jti: str = Field(min_length=8, max_length=64)
    reason: str | None = None


@router.post("/totp/enroll")
async def totp_enroll(
    body: TotpEnrollRequest,
    tenant: Annotated[Tenant, Depends(get_current_tenant)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> dict:
    svc = TotpService(session, tenant.id)
    return await svc.enroll(body.email)


@router.post("/totp/verify")
async def totp_verify(
    body: TotpVerifyRequest,
    tenant: Annotated[Tenant, Depends(get_current_tenant)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> dict:
    svc = TotpService(session, tenant.id)
    ok = await svc.verify(body.email, body.code)
    if not ok:
        raise HTTPException(status_code=401, detail="Invalid TOTP code")
    return {"valid": True}


@router.post("/sessions/revoke")
async def revoke_session(
    body: RevokeSessionRequest,
    tenant: Annotated[Tenant, Depends(get_current_tenant)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> dict:
    svc = SessionDenyService(session, tenant.id)
    row = await svc.revoke(body.jti, body.reason)
    return {"revoked": True, "jti": row.jti}


@router.get("/sessions/check/{jti}")
async def check_session(
    jti: str,
    tenant: Annotated[Tenant, Depends(get_current_tenant)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> dict:
    svc = SessionDenyService(session, tenant.id)
    return {"jti": jti, "revoked": await svc.is_revoked(jti)}
