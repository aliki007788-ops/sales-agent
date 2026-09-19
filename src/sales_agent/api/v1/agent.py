# ==========================================
# src/sales_agent/api/v1/agent.py
# Version: 2.1 — Phase 5 (DB credentials) — Fixed 204 response_model issue
# ==========================================
from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from sales_agent.agent.orchestrator import ActionType, SalesAgent
from sales_agent.api.deps import get_current_tenant
from sales_agent.connectors.base import InboundEvent
from sales_agent.db.session import get_session
from sales_agent.models.tenant import Tenant
from sales_agent.schemas.agent import (
    CampaignStartRequest,
    CampaignStartResponse,
    HandleEventResponse,
    InboundEventPayload,
)
from sales_agent.services.credentials import CredentialService, load_credentials_for_tenant
from sales_agent.services.events import EventService
from sales_agent.services.leads import LeadService

router = APIRouter(prefix="/agent", tags=["agent"])


class ChannelCredentialsBody(BaseModel):
    credentials: dict[str, Any] = Field(
        description="Channel-specific secrets, e.g. {\"token\": \"...\"}"
    )
    webhook_secret: str | None = Field(
        default=None,
        description="Optional; auto-generated if omitted",
    )


class ChannelCredentialRead(BaseModel):
    channel: str
    is_active: bool
    webhook_secret: str | None


async def _build_agent(session: AsyncSession, tenant: Tenant) -> SalesAgent:
    agent = SalesAgent(tenant_id=str(tenant.id))
    creds_map = await load_credentials_for_tenant(session, tenant.id)
    for channel, creds in creds_map.items():
        try:
            agent.register_from_credentials(channel, creds)
        except Exception:
            continue
    return agent


@router.post(
    "/channels/{channel}/credentials",
    response_model=ChannelCredentialRead,
    summary="Store encrypted channel credentials for this tenant.",
)
async def set_channel_credentials(
    channel: str,
    body: ChannelCredentialsBody,
    tenant: Annotated[Tenant, Depends(get_current_tenant)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> ChannelCredentialRead:
    svc = CredentialService(session, tenant.id)
    row = await svc.upsert(
        channel,
        body.credentials,
        webhook_secret=body.webhook_secret,
    )
    return ChannelCredentialRead(
        channel=row.channel,
        is_active=row.is_active,
        webhook_secret=row.webhook_secret,
    )


@router.get(
    "/channels",
    response_model=list[ChannelCredentialRead],
    summary="List configured channels (secrets not exposed).",
)
async def list_channels(
    tenant: Annotated[Tenant, Depends(get_current_tenant)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> list[ChannelCredentialRead]:
    svc = CredentialService(session, tenant.id)
    rows = await svc.list_channels()
    return [
        ChannelCredentialRead(
            channel=r.channel,
            is_active=r.is_active,
            webhook_secret=r.webhook_secret,
        )
        for r in rows
    ]


@router.delete(
    "/channels/{channel}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_model=None,
)
async def deactivate_channel(
    channel: str,
    tenant: Annotated[Tenant, Depends(get_current_tenant)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> None:
    svc = CredentialService(session, tenant.id)
    ok = await svc.deactivate(channel)
    if not ok:
        raise HTTPException(status_code=404, detail="Channel not found")


@router.post("/events", response_model=HandleEventResponse)
async def handle_inbound_event(
    payload: InboundEventPayload,
    tenant: Annotated[Tenant, Depends(get_current_tenant)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> HandleEventResponse:
    event_svc = EventService(session, tenant.id)
    lead_svc = LeadService(session, tenant.id)

    await event_svc.log_inbound(
        payload.channel,
        {
            "external_id": payload.external_id,
            "chat_id": payload.chat_id,
            "text": payload.text,
            "sender_id": payload.sender_id,
            "raw": payload.raw,
        },
    )

    inbound = InboundEvent(
        external_id=payload.external_id,
        chat_id=payload.chat_id,
        text=payload.text,
        sender_id=payload.sender_id,
        raw=payload.raw,
    )

    agent = await _build_agent(session, tenant)
    try:
        result = await agent.handle_event(inbound, channel=payload.channel)
    finally:
        await agent.aclose()

    lead_id: str | None = None
    msg_ext: str | None = None

    if result.action.type == ActionType.CREATE_LEAD and result.action.lead:
        ext = result.action.lead.get("external_id")
        source = result.action.lead.get("source") or payload.channel
        existing = None
        if ext:
            existing = await lead_svc.find_by_external(source, str(ext))
        if existing is None:
            lead = await lead_svc.create_from_dict(result.action.lead)
            lead_id = str(lead.id)
        else:
            lead_id = str(existing.id)

    if result.send_result is not None:
        msg_ext = result.send_result.external_id
        await event_svc.log_outbound(
            payload.channel,
            {
                "external_id": msg_ext,
                "chat_id": payload.chat_id,
                "text": result.action.text,
            },
        )

    return HandleEventResponse(
        success=result.success,
        action_type=result.action.type.value,
        detail=result.detail,
        lead_id=lead_id,
        message_external_id=msg_ext,
    )


@router.post("/campaigns/start", response_model=CampaignStartResponse)
async def start_campaign(
    body: CampaignStartRequest,
    tenant: Annotated[Tenant, Depends(get_current_tenant)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> CampaignStartResponse:
    agent = await _build_agent(session, tenant)
    if body.channel not in agent.connectors:
        await agent.aclose()
        raise HTTPException(
            status_code=400,
            detail=f"Channel '{body.channel}' not configured. "
            f"POST /api/v1/agent/channels/{body.channel}/credentials first.",
        )

    try:
        events = await agent.discover_leads(body.channel, limit=body.limit)
    except Exception as exc:
        await agent.aclose()
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    results: list[HandleEventResponse] = []
    processed = 0

    if body.auto_process:
        event_svc = EventService(session, tenant.id)
        lead_svc = LeadService(session, tenant.id)
        for ev in events:
            await event_svc.log_inbound(
                body.channel,
                {
                    "external_id": ev.external_id,
                    "chat_id": ev.chat_id,
                    "text": ev.text,
                    "raw": ev.raw,
                },
                event_type="discovery",
            )
            result = await agent.handle_event(ev, channel=body.channel)
            lead_id = None
            if result.action.type == ActionType.CREATE_LEAD and result.action.lead:
                ext = result.action.lead.get("external_id")
                source = result.action.lead.get("source") or body.channel
                existing = (
                    await lead_svc.find_by_external(source, str(ext)) if ext else None
                )
                if existing is None:
                    lead = await lead_svc.create_from_dict(result.action.lead)
                    lead_id = str(lead.id)
                else:
                    lead_id = str(existing.id)
            results.append(
                HandleEventResponse(
                    success=result.success,
                    action_type=result.action.type.value,
                    detail=result.detail,
                    lead_id=lead_id,
                )
            )
            processed += 1

    await agent.aclose()
    return CampaignStartResponse(
        channel=body.channel,
        discovered=len(events),
        processed=processed,
        results=results,
    )
