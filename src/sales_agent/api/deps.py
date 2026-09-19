# ==========================================
# src/sales_agent/api/deps.py
# Version: 1.0 — Phase 1 Core Foundation
# ==========================================
from __future__ import annotations

from typing import Annotated

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from sales_agent.db.session import get_session
from sales_agent.models.tenant import Tenant
from sales_agent.security.api_key import extract_prefix, verify_api_key


async def get_current_tenant(
    x_api_key: Annotated[str, Header(alias="X-API-Key")],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> Tenant:
    """Authenticate the caller via X-API-Key header."""
    prefix = extract_prefix(x_api_key)
    stmt = select(Tenant).where(
        Tenant.api_key_prefix == prefix,
        Tenant.is_active.is_(True),
    )
    tenant = (await session.execute(stmt)).scalar_one_or_none()

    if tenant is None or not verify_api_key(x_api_key, tenant.api_key_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key",
        )
    return tenant
