# ==========================================
# tests/unit/services/test_lead_service.py
# ==========================================
from __future__ import annotations

import uuid

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from sales_agent.models.tenant import Tenant
from sales_agent.schemas.lead import LeadCreate, LeadUpdate
from sales_agent.security.api_key import generate_api_key
from sales_agent.services.leads import LeadService


async def _tenant(session: AsyncSession) -> Tenant:
    _, prefix, hashed = generate_api_key()
    t = Tenant(
        name="Svc",
        slug=f"svc-{uuid.uuid4().hex[:8]}",
        api_key_prefix=prefix,
        api_key_hash=hashed,
        plan="pro",
    )
    session.add(t)
    await session.flush()
    return t


@pytest.mark.asyncio
async def test_lead_crud(session: AsyncSession) -> None:
    t = await _tenant(session)
    svc = LeadService(session, t.id)

    lead = await svc.create(
        LeadCreate(source="bale", external_id="x1", name="Ali", score=5)
    )
    assert lead.id is not None
    assert lead.tenant_id == t.id

    found = await svc.find_by_external("bale", "x1")
    assert found is not None
    assert found.id == lead.id

    updated = await svc.update(lead.id, LeadUpdate(status="won", score=90))
    assert updated is not None
    assert updated.status == "won"
    assert updated.score == 90

    rows = await svc.list(source="bale")
    assert len(rows) == 1
