# ==========================================
# TOTP enrollment / verify
# ==========================================
from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from sales_agent.models.totp import UserTotp
from sales_agent.security.totp import (
    decrypt_secret,
    encrypt_secret,
    generate_totp_secret,
    provisioning_uri,
    verify_code,
)


class TotpService:
    def __init__(self, session: AsyncSession, tenant_id: uuid.UUID) -> None:
        self.session = session
        self.tenant_id = tenant_id

    async def enroll(self, email: str) -> dict:
        email = email.lower()
        secret = generate_totp_secret()
        stmt = select(UserTotp).where(
            UserTotp.tenant_id == self.tenant_id, UserTotp.email == email
        )
        row = (await self.session.execute(stmt)).scalar_one_or_none()
        if row is None:
            row = UserTotp(
                tenant_id=self.tenant_id,
                email=email,
                secret_encrypted=encrypt_secret(secret),
                enabled=True,
            )
            self.session.add(row)
        else:
            row.secret_encrypted = encrypt_secret(secret)
            row.enabled = True
        await self.session.flush()
        return {
            "email": email,
            "secret": secret,
            "otpauth_url": provisioning_uri(secret, email),
        }

    async def verify(self, email: str, code: str) -> bool:
        email = email.lower()
        stmt = select(UserTotp).where(
            UserTotp.tenant_id == self.tenant_id,
            UserTotp.email == email,
            UserTotp.enabled.is_(True),
        )
        row = (await self.session.execute(stmt)).scalar_one_or_none()
        if row is None:
            return False
        secret = decrypt_secret(row.secret_encrypted)
        return verify_code(secret, code)
