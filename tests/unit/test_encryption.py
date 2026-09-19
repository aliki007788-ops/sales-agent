# ==========================================
# tests/unit/test_encryption.py
# ==========================================
from __future__ import annotations

from sales_agent.security.encryption import decrypt_dict, encrypt_dict


def test_encrypt_decrypt_roundtrip() -> None:
    data = {"token": "secret-123", "nested": {"a": 1}}
    blob = encrypt_dict(data)
    assert blob != str(data)
    assert "secret" not in blob
    restored = decrypt_dict(blob)
    assert restored == data


def test_decrypt_invalid_raises() -> None:
    import pytest

    with pytest.raises(ValueError):
        decrypt_dict("not-a-valid-fernet-token")
