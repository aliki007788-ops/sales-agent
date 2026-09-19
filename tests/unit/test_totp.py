from sales_agent.security.totp import generate_totp_secret, verify_code
import pyotp


def test_totp_roundtrip():
    secret = generate_totp_secret()
    code = pyotp.TOTP(secret).now()
    assert verify_code(secret, code) is True
    assert verify_code(secret, "000000") is False
