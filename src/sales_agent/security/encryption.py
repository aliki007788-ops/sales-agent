# ==========================================
# src/sales_agent/security/encryption.py
# Version: 1.0 — Phase 5
# ==========================================
from __future__ import annotations

import base64
import hashlib
import json
from typing import Any

from cryptography.fernet import Fernet, InvalidToken

from sales_agent.config import get_settings


def _fernet() -> Fernet:
    """Derive a stable Fernet key from SECRET_KEY."""
    settings = get_settings()
    digest = hashlib.sha256(settings.secret_key.encode("utf-8")).digest()
    key = base64.urlsafe_b64encode(digest)
    return Fernet(key)


def encrypt_dict(data: dict[str, Any]) -> str:
    raw = json.dumps(data, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    return _fernet().encrypt(raw).decode("utf-8")


def decrypt_dict(token: str) -> dict[str, Any]:
    try:
        raw = _fernet().decrypt(token.encode("utf-8"))
    except InvalidToken as exc:
        raise ValueError("Invalid or corrupted credential blob") from exc
    return json.loads(raw.decode("utf-8"))
