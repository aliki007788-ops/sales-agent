# ==========================================
# Billing / quota API
# ==========================================
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends

from sales_agent.api.deps import get_current_tenant
from sales_agent.billing.plans import PLANS, get_plan
from sales_agent.billing.quota import quota_service
from sales_agent.models.tenant import Tenant

router = APIRouter(prefix="/billing", tags=["billing"])


@router.get("/plans")
async def list_plans() -> list[dict]:
    return [
        {
            "name": p.name,
            "display_name": p.display_name,
            "monthly_price_irr": p.monthly_price_irr,
            "max_messages_per_month": p.max_messages_per_month,
            "max_llm_calls_per_month": p.max_llm_calls_per_month,
            "max_leads_per_month": p.max_leads_per_month,
            "max_channels": p.max_channels,
            "max_seats": p.max_seats,
        }
        for p in PLANS.values()
    ]


@router.get("/usage")
async def usage(
    tenant: Annotated[Tenant, Depends(get_current_tenant)],
) -> dict:
    return {
        "plan": tenant.plan,
        "limits": {
            "messages": get_plan(tenant.plan).max_messages_per_month,
            "llm_calls": get_plan(tenant.plan).max_llm_calls_per_month,
            "leads": get_plan(tenant.plan).max_leads_per_month,
        },
        "usage": quota_service.snapshot(str(tenant.id), tenant.plan),
    }
