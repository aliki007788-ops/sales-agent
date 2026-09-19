# ==========================================
# src/sales_agent/connectors/exceptions.py
# Version: 1.0 — Phase 2
# ==========================================
from __future__ import annotations


class ConnectorError(Exception):
    """Base exception for all connector failures."""


class ConnectorAuthError(ConnectorError):
    """Invalid or expired credentials / token."""


class ConnectorUnavailable(ConnectorError):
    """Upstream service is down or unreachable."""


class ConnectorRateLimited(ConnectorError):
    """Rate limit exceeded by the upstream API."""


class ConnectorBadRequest(ConnectorError):
    """Invalid payload or parameters sent to the upstream API."""
