# ==========================================
# Session denylist service
# ==========================================
from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from sales_agent.models.session_deny import RevokedSession


class SessionDenyService:
    def __init__(self, session: AsyncSession, tenant_id: uuid.UUID) -> None:
        self.session = session
        self.tenant_id = tenant_id

    async def revoke(self, jti: str, reason: str | None = None) -> RevokedSession:
        row = RevokedSession(tenant_id=self.tenant_id, jti=jti, reason=reason)
        self.session.add(row)
        await self.session.flush()
        await self.session.refresh(row)
        return row

    async def is_revoked(self, jti: str) -> bool:
        stmt = select(RevokedSession.id).where(RevokedSession.jti == jti)
        return (await self.session.execute(stmt)).scalar_one_or_none() is not None
