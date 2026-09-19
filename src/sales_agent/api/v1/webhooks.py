# ==========================================
# src/sales_agent/api/v1/webhooks.py
# Version: 1.0 — Phase 5
#
# Public webhook endpoints (no X-API-Key).
# Authenticated via path tenant_id + webhook_secret header/query.
# ==========================================
from __future__ import annotations

import uuid
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from sales_agent.agent.orchestrator import ActionType, SalesAgent
from sales_agent.connectors.base import InboundEvent
from sales_agent.db.session import get_session
from sales_agent.models.channel_credential import ChannelCredential
from sales_agent.models.tenant import Tenant
from sales_agent.schemas.agent import HandleEventResponse
from sales_agent.security.encryption import decrypt_dict
from sales_agent.services.events import EventService
from sales_agent.services.leads import LeadService
from sales_agent.worker.queue import get_queue

router = APIRouter(prefix="/webhooks", tags=["webhooks"])


async def _resolve_tenant_channel(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    channel: str,
    secret: str | None,
) -> tuple[Tenant, ChannelCredential, dict[str, Any]]:
    tenant = (
        await session.execute(
            select(Tenant).where(Tenant.id == tenant_id, Tenant.is_active.is_(True))
        )
    ).scalar_one_or_none()
    if tenant is None:
        raise HTTPException(status_code=404, detail="Tenant not found")

    cred = (
        await session.execute(
            select(ChannelCredential).where(
                ChannelCredential.tenant_id == tenant_id,
                ChannelCredential.channel == channel.lower(),
                ChannelCredential.is_active.is_(True),
            )
        )
    ).scalar_one_or_none()
    if cred is None:
        raise HTTPException(status_code=404, detail="Channel not configured")

    if cred.webhook_secret and secret != cred.webhook_secret:
        raise HTTPException(status_code=401, detail="Invalid webhook secret")

    try:
        credentials = decrypt_dict(cred.credentials_encrypted)
    except ValueError as exc:
        raise HTTPException(status_code=500, detail="Credential decrypt failed") from exc

    return tenant, cred, credentials


def _parse_telegram_like(body: dict[str, Any]) -> InboundEvent | None:
    """Normalize Telegram/Bale update payload."""
    msg = body.get("message") or body.get("edited_message") or body.get("channel_post")
    if not msg and "update_id" in body:
        # already flat or nested
        msg = body
    if not isinstance(msg, dict):
        return None
    # if body is full update
    if "message" in body or "edited_message" in body:
        update_id = str(body.get("update_id", ""))
        message = body.get("message") or body.get("edited_message") or {}
    else:
        update_id = str(body.get("update_id") or body.get("message_id") or "")
        message = msg

    chat = message.get("chat") or {}
    from_user = message.get("from") or {}
    return InboundEvent(
        external_id=update_id or str(message.get("message_id", "")),
        chat_id=str(chat.get("id", "")),
        text=message.get("text"),
        sender_id=str(from_user.get("id")) if from_user else None,
        raw=body,
    )


@router.post(
    "/{tenant_id}/{channel}",
    response_model=HandleEventResponse,
    summary="Inbound webhook for a channel (Telegram/Bale style).",
)
async def channel_webhook(
    tenant_id: uuid.UUID,
    channel: str,
    request: Request,
    session: Annotated[AsyncSession, Depends(get_session)],
    x_webhook_secret: Annotated[str | None, Header(alias="X-Webhook-Secret")] = None,
    secret: Annotated[str | None, Query()] = None,
    async_mode: Annotated[bool, Query()] = False,
) -> HandleEventResponse | dict[str, str]:
    secret_val = x_webhook_secret or secret
    tenant, _cred, credentials = await _resolve_tenant_channel(
        session, tenant_id, channel, secret_val
    )

    try:
        body = await request.json()
    except Exception as exc:
        raise HTTPException(status_code=400, detail="Invalid JSON body") from exc

    if not isinstance(body, dict):
        raise HTTPException(status_code=400, detail="JSON object required")

    inbound = _parse_telegram_like(body)
    if inbound is None:
        # generic fallback
        inbound = InboundEvent(
            external_id=str(body.get("id") or body.get("update_id") or ""),
            chat_id=str(body.get("chat_id") or ""),
            text=body.get("text"),
            sender_id=str(body.get("sender_id")) if body.get("sender_id") else None,
            raw=body,
        )

    if async_mode:
        q = get_queue()
        await q.enqueue(
            "process_inbound",
            {
                "tenant_id": str(tenant.id),
                "channel": channel.lower(),
                "event": {
                    "external_id": inbound.external_id,
                    "chat_id": inbound.chat_id,
                    "text": inbound.text,
                    "sender_id": inbound.sender_id,
                    "raw": inbound.raw,
                },
            },
            tenant_id=str(tenant.id),
        )
        return {"status": "queued"}  # type: ignore[return-value]

    return await _process_inbound(session, tenant, channel.lower(), inbound, credentials)


async def _process_inbound(
    session: AsyncSession,
    tenant: Tenant,
    channel: str,
    inbound: InboundEvent,
    credentials: dict[str, Any],
) -> HandleEventResponse:
    event_svc = EventService(session, tenant.id)
    lead_svc = LeadService(session, tenant.id)

    await event_svc.log_inbound(
        channel,
        {
            "external_id": inbound.external_id,
            "chat_id": inbound.chat_id,
            "text": inbound.text,
            "sender_id": inbound.sender_id,
            "raw": inbound.raw,
        },
    )

    agent = SalesAgent(tenant_id=str(tenant.id))
    try:
        agent.register_from_credentials(channel, credentials)
    except Exception:
        pass

    try:
        result = await agent.handle_event(inbound, channel=channel)
    finally:
        await agent.aclose()

    lead_id = None
    msg_ext = None

    if result.action.type == ActionType.CREATE_LEAD and result.action.lead:
        ext = result.action.lead.get("external_id")
        source = result.action.lead.get("source") or channel
        existing = await lead_svc.find_by_external(source, str(ext)) if ext else None
        if existing is None:
            lead = await lead_svc.create_from_dict(result.action.lead)
            lead_id = str(lead.id)
        else:
            lead_id = str(existing.id)

    if result.send_result is not None:
        msg_ext = result.send_result.external_id
        await event_svc.log_outbound(
            channel,
            {
                "external_id": msg_ext,
                "chat_id": inbound.chat_id,
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
