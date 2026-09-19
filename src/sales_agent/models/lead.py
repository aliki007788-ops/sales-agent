# ==========================================
# src/sales_agent/models/lead.py
# Version: 1.0 — Phase 1 Core Foundation
# ==========================================
from __future__ import annotations

import uuid

from sqlalchemy import JSON, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from sales_agent.db.base import Base, TimestampMixin


class Lead(Base, TimestampMixin):
    """A sales lead discovered or created by the agent."""

    __tablename__ = "leads"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    source: Mapped[str] = mapped_column(String(40), nullable=False)
    external_id: Mapped[str | None] = mapped_column(String(120), index=True)
    name: Mapped[str | None] = mapped_column(String(120))
    contact: Mapped[str | None] = mapped_column(String(180))
    score: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="new", nullable=False)
    notes: Mapped[str | None] = mapped_column(Text)
    # JSON works on both SQLite (tests) and PostgreSQL
    meta: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)


    tenant: Mapped["Tenant"] = relationship(back_populates="leads")  # noqa: F821

    def __repr__(self) -> str:
        return f"<Lead id={self.id} source={self.source} score={self.score}>"
