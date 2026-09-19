from fastapi import APIRouter

from sales_agent.api.v1 import agent, billing, events, leads, security_api, team, tenants, webhooks

router = APIRouter(prefix="/api/v1")
router.include_router(tenants.router)
router.include_router(leads.router)
router.include_router(events.router)
router.include_router(agent.router)
router.include_router(webhooks.router)
router.include_router(billing.router)
router.include_router(team.router)
router.include_router(security_api.router)

__all__ = ["router"]
