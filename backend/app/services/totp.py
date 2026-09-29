"""Two-step sign-in for the admin account: 6-digit codes from an authenticator app (TOTP, RFC 6238).

The secret is stored encrypted with a key derived from SECRET_KEY (changing SECRET_KEY means setting
two-step sign-in up again; scripts/reset_admin_2fa.py clears it). A code is accepted once: the time
step it belongs to is remembered, so a code seen over someone's shoulder can't be replayed.
"""
import base64
import hashlib
import hmac
import time

import pyotp
import segno
from cryptography.fernet import Fernet, InvalidToken

from app.config import APP_NAME, SECRET_KEY
from app.models import User

STEP_S = 30
_fernet = Fernet(base64.urlsafe_b64encode(hashlib.sha256(f"totp:{SECRET_KEY}".encode()).digest()))


def new_secret() -> str:
    return pyotp.random_base32()


def seal(secret: str) -> str:
    return _fernet.encrypt(secret.encode()).decode()


def _open(sealed: str | None) -> str | None:
    if not sealed:
        return None
    try:
        return _fernet.decrypt(sealed.encode()).decode()
    except InvalidToken:
        return None


def enabled(user: User) -> bool:
    return user.totp_enabled_at is not None


def provisioning(secret: str, email: str) -> dict:
    """What the authenticator app needs: a QR code (SVG) and the same thing as text."""
    uri = pyotp.TOTP(secret).provisioning_uri(name=email, issuer_name=APP_NAME)
    qr = segno.make(uri, error="m")
    return {"secret": secret, "uri": uri, "qr_svg_data_uri": qr.svg_data_uri(scale=5, border=2)}


def verify(user: User, code: str) -> bool:
    """Check a code against the user's (pending or active) secret, allowing one step of clock drift.
    Accepted codes can't be used again."""
    secret = _open(user.totp_secret)
    code = (code or "").strip().replace(" ", "")
    if not secret or not code.isdigit() or len(code) != 6:
        return False
    totp = pyotp.TOTP(secret)
    now = int(time.time()) // STEP_S
    for step in (now - 1, now, now + 1):
        if step <= (user.totp_last_step or -1):
            continue
        if hmac.compare_digest(totp.at(step * STEP_S), code):
            user.totp_last_step = step
            return True
    return False
