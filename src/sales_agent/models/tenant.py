# ==========================================
# src/sales_agent/models/tenant.py
# Version: 1.0 — Phase 1 Core Foundation
# ==========================================
from __future__ import annotations

import uuid

from sqlalchemy import Boolean, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from sales_agent.db.base import Base, TimestampMixin


class Tenant(Base, TimestampMixin):
    """A customer account (multi-tenant root)."""

    __tablename__ = "tenants"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    slug: Mapped[str] = mapped_column(String(60), unique=True, index=True, nullable=False)

    # API key: prefix for O(1) lookup, hash for verification
    api_key_prefix: Mapped[str] = mapped_column(String(16), index=True, nullable=False)
    api_key_hash: Mapped[str] = mapped_column(String(128), nullable=False)

    plan: Mapped[str] = mapped_column(String(20), default="free", nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    leads: Mapped[list["Lead"]] = relationship(  # noqa: F821
        back_populates="tenant", cascade="all, delete-orphan"
    )
    events: Mapped[list["Event"]] = relationship(  # noqa: F821
        back_populates="tenant", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Tenant id={self.id} slug={self.slug} plan={self.plan}>"
