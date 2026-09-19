# ==========================================
# src/sales_agent/services/credentials.py
# Version: 1.0 — Phase 5
# ==========================================
from __future__ import annotations

import secrets
import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from sales_agent.models.channel_credential import ChannelCredential
from sales_agent.security.encryption import decrypt_dict, encrypt_dict


class CredentialService:
    def __init__(self, session: AsyncSession, tenant_id: uuid.UUID) -> None:
        self.session = session
        self.tenant_id = tenant_id

    async def upsert(
        self,
        channel: str,
        credentials: dict[str, Any],
        *,
        webhook_secret: str | None = None,
        is_active: bool = True,
    ) -> ChannelCredential:
        channel = channel.lower().strip()
        stmt = select(ChannelCredential).where(
            ChannelCredential.tenant_id == self.tenant_id,
            ChannelCredential.channel == channel,
        )
        row = (await self.session.execute(stmt)).scalar_one_or_none()
        blob = encrypt_dict(credentials)
        secret = webhook_secret or (row.webhook_secret if row else secrets.token_urlsafe(24))

        if row is None:
            row = ChannelCredential(
                tenant_id=self.tenant_id,
                channel=channel,
                credentials_encrypted=blob,
                webhook_secret=secret,
                is_active=is_active,
            )
            self.session.add(row)
        else:
            row.credentials_encrypted = blob
            row.is_active = is_active
            if webhook_secret is not None:
                row.webhook_secret = webhook_secret
        await self.session.flush()
        await self.session.refresh(row)
        return row

    async def get(self, channel: str) -> ChannelCredential | None:
        stmt = select(ChannelCredential).where(
            ChannelCredential.tenant_id == self.tenant_id,
            ChannelCredential.channel == channel.lower(),
            ChannelCredential.is_active.is_(True),
        )
        return (await self.session.execute(stmt)).scalar_one_or_none()

    async def get_decrypted(self, channel: str) -> dict[str, Any] | None:
        row = await self.get(channel)
        if row is None:
            return None
        return decrypt_dict(row.credentials_encrypted)

    async def list_channels(self) -> list[ChannelCredential]:
        stmt = (
            select(ChannelCredential)
            .where(ChannelCredential.tenant_id == self.tenant_id)
            .order_by(ChannelCredential.channel)
        )
        return list((await self.session.execute(stmt)).scalars().all())

    async def deactivate(self, channel: str) -> bool:
        stmt = select(ChannelCredential).where(
            ChannelCredential.tenant_id == self.tenant_id,
            ChannelCredential.channel == channel.lower(),
        )
        row = (await self.session.execute(stmt)).scalar_one_or_none()
        if row is None:
            return False
        row.is_active = False
        await self.session.flush()
        return True


async def load_credentials_for_tenant(
    session: AsyncSession, tenant_id: uuid.UUID
) -> dict[str, dict[str, Any]]:
    """Return {channel: credentials_dict} for all active channels."""
    stmt = select(ChannelCredential).where(
        ChannelCredential.tenant_id == tenant_id,
        ChannelCredential.is_active.is_(True),
    )
    rows = (await session.execute(stmt)).scalars().all()
    out: dict[str, dict[str, Any]] = {}
    for row in rows:
        try:
            out[row.channel] = decrypt_dict(row.credentials_encrypted)
        except ValueError:
            continue
    return out
