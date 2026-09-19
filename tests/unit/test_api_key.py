# ==========================================
# tests/unit/test_api_key.py
# ==========================================
from __future__ import annotations

from sales_agent.security.api_key import (
    extract_prefix,
    generate_api_key,
    hash_api_key,
    verify_api_key,
)


def test_generate_api_key_shape() -> None:
    plaintext, prefix, hashed = generate_api_key()
    assert plaintext.startswith("asa_")
    assert prefix.startswith("asa_")
    assert len(prefix) == 4 + 6  # "asa_" + 6 chars
    assert hashed.startswith("$2b$") or hashed.startswith("$2a$")


def test_verify_api_key_roundtrip() -> None:
    plaintext, _, hashed = generate_api_key()
    assert verify_api_key(plaintext, hashed) is True
    assert verify_api_key(plaintext + "x", hashed) is False


def test_extract_prefix_matches() -> None:
    plaintext, prefix, _ = generate_api_key()
    assert extract_prefix(plaintext) == prefix
