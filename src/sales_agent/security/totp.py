# ==========================================
# TOTP helpers
# ==========================================
from __future__ import annotations

import pyotp

from sales_agent.security.encryption import decrypt_dict, encrypt_dict


def generate_totp_secret() -> str:
    return pyotp.random_base32()


def encrypt_secret(secret: str) -> str:
    return encrypt_dict({"secret": secret})


def decrypt_secret(blob: str) -> str:
    return str(decrypt_dict(blob)["secret"])


def provisioning_uri(secret: str, email: str, issuer: str = "SalesAgent") -> str:
    return pyotp.TOTP(secret).provisioning_uri(name=email, issuer_name=issuer)


def verify_code(secret: str, code: str) -> bool:
    return pyotp.TOTP(secret).verify(code, valid_window=1)
