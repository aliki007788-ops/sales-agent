# ==========================================
# tests/unit/connectors/test_registry.py
# ==========================================
from __future__ import annotations

import pytest

from sales_agent.connectors import (
    BaleConnector,
    DivarConnector,
    EitaaConnector,
    EmallsConnector,
    RubikaConnector,
    TelegramConnector,
    TorbConnector,
    available_channels,
    get_connector,
)
from sales_agent.connectors.exceptions import ConnectorError


def test_available_channels_complete() -> None:
    ch = available_channels()
    for name in ("bale", "telegram", "eitaa", "rubika", "divar", "torb", "emalls"):
        assert name in ch


def test_get_connector_messaging() -> None:
    assert isinstance(get_connector("bale", {"token": "x:y"}), BaleConnector)
    assert isinstance(get_connector("telegram", {"token": "x:y"}), TelegramConnector)
    assert isinstance(get_connector("eitaa", {"token": "x"}), EitaaConnector)
    assert isinstance(get_connector("rubika", {"token": "x"}), RubikaConnector)


def test_get_connector_discovery() -> None:
    assert isinstance(get_connector("divar", {"city": "tehran"}), DivarConnector)
    assert isinstance(get_connector("torb", {"base_url": "https://example.com"}), TorbConnector)
    assert isinstance(get_connector("emalls", {"base_url": "https://example.com"}), EmallsConnector)


def test_get_connector_unknown() -> None:
    with pytest.raises(ConnectorError, match="Unknown channel"):
        get_connector("unknown_channel", {"token": "x"})
