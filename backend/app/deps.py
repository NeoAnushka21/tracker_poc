from fastapi import Cookie, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import User
from app.security import COOKIE_NAME, decode_session_token


def current_user(
    session: str | None = Cookie(default=None, alias=COOKIE_NAME),
    db: Session = Depends(get_db),
) -> User:
    decoded = decode_session_token(session) if session else None
    user = db.get(User, decoded[0]) if decoded else None
    # A token from before the account's sessions were ended (password change, log out everywhere).
    if user is not None and decoded[1] != (user.session_version or 0):
        user = None
    if user is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Not logged in")
    return user


def is_admin(user: User) -> bool:
    from app.config import ADMIN_EMAILS
    return user.email.lower() in ADMIN_EMAILS


def admin_user(user: User = Depends(current_user)) -> User:
    if not is_admin(user):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Admins only")
    return user


def onboarded_user(user: User = Depends(current_user)) -> User:
    from app.config import CONSENT_VERSION
    if user.consent_version != CONSENT_VERSION:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Please accept the data consent first")
    if not user.onboarded:
        raise HTTPException(status.HTTP_409_CONFLICT, "Finish onboarding first")
    return user
