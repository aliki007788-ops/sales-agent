# ==========================================
# src/sales_agent/models/channel_credential.py
# Version: 1.0 — Phase 5
# ==========================================
from __future__ import annotations

import uuid

from sqlalchemy import Boolean, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from sales_agent.db.base import Base, TimestampMixin


class ChannelCredential(Base, TimestampMixin):
    """Encrypted channel credentials per tenant."""

    __tablename__ = "channel_credentials"
    __table_args__ = (
        UniqueConstraint("tenant_id", "channel", name="uq_tenant_channel"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    channel: Mapped[str] = mapped_column(String(40), nullable=False)
    # Fernet-encrypted JSON blob
    credentials_encrypted: Mapped[str] = mapped_column(Text, nullable=False)
    # Optional shared secret for webhook verification
    webhook_secret: Mapped[str | None] = mapped_column(String(128), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    tenant: Mapped["Tenant"] = relationship()  # noqa: F821

    def __repr__(self) -> str:
        return f"<ChannelCredential tenant={self.tenant_id} channel={self.channel}>"
