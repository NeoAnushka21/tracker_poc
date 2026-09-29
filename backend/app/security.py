"""Password hashing (Argon2id) and session tokens (JWT in an httpOnly cookie).

Argon2id with OWASP's recommended minimum (19 MiB memory, 2 passes, 1 lane). Hashes made before
2026-09-29 are scrypt (N=2^14, below OWASP's advice); they still verify and are replaced with
Argon2id on the user's next successful login (`needs_rehash`)."""
import base64
import hashlib
import hmac
import secrets
from datetime import datetime, timedelta, timezone

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError

from app.config import SECRET_KEY, SESSION_DAYS

_ARGON2 = PasswordHasher(time_cost=2, memory_cost=19 * 1024, parallelism=1)
_SCRYPT = {"n": 2**14, "r": 8, "p": 1, "dklen": 64}   # legacy hashes only
COOKIE_NAME = "session"
# Checked against when the email doesn't exist, so an unknown email takes as long as a wrong password.
_DUMMY_HASH = _ARGON2.hash(secrets.token_urlsafe(16))


def hash_password(password: str) -> str:
    return _ARGON2.hash(password)


def verify_password(password: str, stored: str) -> bool:
    if stored.startswith("$argon2"):
        try:
            return _ARGON2.verify(stored, password)
        except (VerifyMismatchError, VerificationError, InvalidHashError):
            return False
    return _verify_scrypt(password, stored)


def needs_rehash(stored: str) -> bool:
    """True for legacy scrypt hashes or Argon2 hashes made with older settings."""
    return not stored.startswith("$argon2") or _ARGON2.check_needs_rehash(stored)


def burn_verify_time(password: str) -> None:
    """Do the same work as a real check, for logins with an unknown email (no timing difference)."""
    verify_password(password, _DUMMY_HASH)


def _verify_scrypt(password: str, stored: str) -> bool:
    try:
        scheme, salt_b64, digest_b64 = stored.split("$")
    except ValueError:
        return False
    if scheme != "scrypt":
        return False
    digest = hashlib.scrypt(password.encode(), salt=base64.b64decode(salt_b64), **_SCRYPT)
    return hmac.compare_digest(digest, base64.b64decode(digest_b64))


def create_session_token(user_id: int, session_version: int = 0, lifetime: timedelta | None = None) -> str:
    now = datetime.now(timezone.utc)
    lifetime = lifetime or timedelta(days=SESSION_DAYS)
    payload = {"sub": str(user_id), "sv": session_version, "iat": now, "exp": now + lifetime}
    return jwt.encode(payload, SECRET_KEY, algorithm="HS256")


def decode_session_token(token: str) -> tuple[int, int] | None:
    """(user id, session version) from a valid token. Tokens from before versions count as 0."""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
        return int(payload["sub"]), int(payload.get("sv", 0))
    except (jwt.PyJWTError, KeyError, ValueError, TypeError):
        return None
