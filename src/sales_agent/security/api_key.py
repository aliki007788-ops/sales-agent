# ==========================================
# src/sales_agent/security/api_key.py
# Version: 1.1 — Phase 1 (bcrypt direct)
# ==========================================
from __future__ import annotations

import secrets

import bcrypt

from sales_agent.config import get_settings


def generate_api_key() -> tuple[str, str, str]:
    """Return (plaintext, prefix, hash)."""
    settings = get_settings()
    body = secrets.token_urlsafe(settings.api_key_length)[: settings.api_key_length]
    plaintext = f"{settings.api_key_prefix}{body}"
    prefix = plaintext[: len(settings.api_key_prefix) + 6]
    return plaintext, prefix, hash_api_key(plaintext)


def hash_api_key(plaintext: str) -> str:
    """Hash API key with bcrypt. Returns utf-8 string."""
    raw = plaintext.encode("utf-8")[:72]
    return bcrypt.hashpw(raw, bcrypt.gensalt(rounds=12)).decode("utf-8")


def verify_api_key(plaintext: str, hashed: str) -> bool:
    try:
        raw = plaintext.encode("utf-8")[:72]
        return bcrypt.checkpw(raw, hashed.encode("utf-8"))
    except (ValueError, TypeError):
        return False


def extract_prefix(plaintext: str) -> str:
    settings = get_settings()
    return plaintext[: len(settings.api_key_prefix) + 6]
