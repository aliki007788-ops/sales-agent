# ==========================================
# src/sales_agent/models/event.py
# Version: 1.0 — Phase 1 Core Foundation
# ==========================================
from __future__ import annotations

import uuid

from sqlalchemy import JSON, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from sales_agent.db.base import Base, TimestampMixin


class Event(Base, TimestampMixin):
    """An inbound/outbound event (message, webhook, agent action)."""

    __tablename__ = "events"

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
    direction: Mapped[str] = mapped_column(String(10), nullable=False)  # in / out
    event_type: Mapped[str] = mapped_column(String(40), nullable=False)
    # JSON works on both SQLite (tests) and PostgreSQL
    payload: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)


    tenant: Mapped["Tenant"] = relationship(back_populates="events")  # noqa: F821

    def __repr__(self) -> str:
        return f"<Event id={self.id} channel={self.channel} type={self.event_type}>"
