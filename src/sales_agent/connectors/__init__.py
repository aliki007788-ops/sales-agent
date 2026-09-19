# ==========================================
# src/sales_agent/connectors/__init__.py
# Version: 2.0 — Phase 2b (all channels registered)
# ==========================================
from __future__ import annotations

from typing import Any

from sales_agent.connectors.bale import BaleConnector
from sales_agent.connectors.base import (
    BaseConnector,
    InboundEvent,
    OutboundMessage,
    SendResult,
)
from sales_agent.connectors.divar import DivarConnector
from sales_agent.connectors.eitaa import EitaaConnector
from sales_agent.connectors.exceptions import (
    ConnectorAuthError,
    ConnectorBadRequest,
    ConnectorError,
    ConnectorRateLimited,
    ConnectorUnavailable,
)
from sales_agent.connectors.marketplace import EmallsConnector, TorbConnector
from sales_agent.connectors.rubika import RubikaConnector
from sales_agent.connectors.telegram import TelegramConnector

_REGISTRY: dict[str, type[BaseConnector]] = {
    "bale": BaleConnector,
    "telegram": TelegramConnector,
    "eitaa": EitaaConnector,
    "rubika": RubikaConnector,
    "divar": DivarConnector,
    "torb": TorbConnector,
    "emalls": EmallsConnector,
}


def get_connector(channel: str, credentials: dict[str, Any], **kwargs: Any) -> BaseConnector:
    """Factory: create a connector by channel name."""
    cls = _REGISTRY.get(channel.lower())
    if cls is None:
        raise ConnectorError(
            f"Unknown channel: {channel}. Available: {sorted(_REGISTRY)}"
        )
    return cls(credentials, **kwargs)


def available_channels() -> list[str]:
    return sorted(_REGISTRY.keys())


__all__ = [
    "BaseConnector",
    "OutboundMessage",
    "SendResult",
    "InboundEvent",
    "BaleConnector",
    "TelegramConnector",
    "EitaaConnector",
    "RubikaConnector",
    "DivarConnector",
    "TorbConnector",
    "EmallsConnector",
    "ConnectorError",
    "ConnectorAuthError",
    "ConnectorUnavailable",
    "ConnectorRateLimited",
    "ConnectorBadRequest",
    "get_connector",
    "available_channels",
]
