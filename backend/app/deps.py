from fastapi import Cookie, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import User
from app.security import COOKIE_NAME, decode_session_token


def current_user(
    session: str | None = Cookie(default=None, alias=COOKIE_NAME),
    db: Session = Depends(get_db),
) -> User:
    user_id = decode_session_token(session) if session else None
    user = db.get(User, user_id) if user_id else None
    if user is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Not logged in")
    return user


def onboarded_user(user: User = Depends(current_user)) -> User:
    if not user.onboarded:
        raise HTTPException(status.HTTP_409_CONFLICT, "Finish onboarding first")
    return user
