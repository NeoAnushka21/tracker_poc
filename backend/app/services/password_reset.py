"""Forgot password: one-time links that work for PASSWORD_RESET_MINUTES.

Only a SHA-256 of the token is stored. The link puts the token after "#", so it never reaches
server logs. Using it sets the new password and signs the account out everywhere.
"""
import hashlib
import secrets
from datetime import timedelta

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app import config
from app.models import PasswordReset, User, utcnow
from app.security import hash_password


class ResetError(Exception):
    """The link is unknown, used or expired; the message is shown to the user."""


def _digest(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def create_link(db: Session, user: User) -> str:
    """A new reset link for this user (older unused links stop working)."""
    _retire_open_links(db, user.id)
    token = secrets.token_urlsafe(32)
    db.add(PasswordReset(user_id=user.id, token_hash=_digest(token),
                         expires_at=utcnow() + timedelta(minutes=config.PASSWORD_RESET_MINUTES)))
    return f"{config.PUBLIC_APP_URL}/reset-password#token={token}"


def email_text(link: str) -> str:
    return (
        f"Someone (hopefully you) asked to reset the password for your {config.APP_NAME} account.\n\n"
        f"Set a new password here (the link works once, for {config.PASSWORD_RESET_MINUTES} minutes):\n{link}\n\n"
        "If you didn't ask for this, ignore this email: your password stays as it is.\n"
    )


def use_link(db: Session, token: str, new_password: str) -> User:
    row = db.scalars(select(PasswordReset).where(PasswordReset.token_hash == _digest(token))).first()
    if row is None or row.used_at is not None or row.expires_at < utcnow():
        raise ResetError("This reset link has expired or was already used. Ask for a new one.")
    user = db.get(User, row.user_id)
    if user is None:
        raise ResetError("This reset link has expired or was already used. Ask for a new one.")
    row.used_at = utcnow()
    _retire_open_links(db, user.id)
    user.hashed_password = hash_password(new_password)
    user.session_version = (user.session_version or 0) + 1   # sign out everywhere
    return user


def _retire_open_links(db: Session, user_id: int) -> None:
    db.execute(update(PasswordReset)
               .where(PasswordReset.user_id == user_id, PasswordReset.used_at.is_(None))
               .values(used_at=utcnow()))
