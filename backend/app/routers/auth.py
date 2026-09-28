from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app import config
from app.config import CONSENT_TEXT, CONSENT_VERSION, COOKIE_SECURE, SESSION_DAYS
from app.db import get_db
from app.deps import current_user, is_admin
from app.models import User, utcnow
from app.routers.profile import user_to_dict
from app.schemas import Credentials, DeleteAccountIn, PasswordChangeIn, RegisterIn
from app.services.accounts import delete_user_and_data
from app.security import COOKIE_NAME, create_session_token, hash_password, verify_password

router = APIRouter(prefix="/api/auth", tags=["auth"])


def _set_session_cookie(response: Response, user_id: int) -> None:
    response.set_cookie(
        COOKIE_NAME,
        create_session_token(user_id),
        max_age=SESSION_DAYS * 86400,
        httponly=True,
        samesite="lax",
        secure=COOKIE_SECURE,
    )


def _record_login(user: User) -> None:
    user.last_login_at = utcnow()
    user.login_count = (user.login_count or 0) + 1


@router.get("/consent-text")
def consent_text():
    return {"version": CONSENT_VERSION, "text": CONSENT_TEXT}


@router.post("/register", status_code=status.HTTP_201_CREATED)
def register(body: RegisterIn, response: Response, db: Session = Depends(get_db)):
    if not body.consent:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "Please accept the data consent to create an account")
    if body.email in config.ADMIN_EMAILS:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "This email is reserved. Use Admin login.")
    if db.scalars(select(User).where(User.email == body.email)).first():
        raise HTTPException(status.HTTP_409_CONFLICT, "An account with this email already exists")
    user = User(email=body.email, hashed_password=hash_password(body.password),
                consent_at=utcnow(), consent_version=CONSENT_VERSION)
    _record_login(user)
    db.add(user)
    db.commit()
    _set_session_cookie(response, user.id)
    return user_to_dict(db, user)


@router.post("/login")
def login(body: Credentials, response: Response, db: Session = Depends(get_db)):
    user = _check_credentials(db, body)
    if is_admin(user):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "This is the admin account. Use Admin login.")
    _record_login(user)
    db.commit()
    _set_session_cookie(response, user.id)
    return user_to_dict(db, user)


@router.post("/admin-login")
def admin_login(body: Credentials, response: Response, db: Session = Depends(get_db)):
    user = _check_credentials(db, body)
    if not is_admin(user):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "This account isn't an admin. Use the regular login.")
    _record_login(user)
    db.commit()
    _set_session_cookie(response, user.id)
    return user_to_dict(db, user)


def _check_credentials(db: Session, body: Credentials) -> User:
    user = db.scalars(select(User).where(User.email == body.email)).first()
    if user is None or not verify_password(body.password, user.hashed_password):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Wrong email or password")
    return user


@router.post("/change-password")
def change_password(body: PasswordChangeIn, user: User = Depends(current_user), db: Session = Depends(get_db)):
    if not verify_password(body.current_password, user.hashed_password):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Current password is wrong")
    user.hashed_password = hash_password(body.new_password)
    db.commit()
    return {"ok": True}


@router.post("/delete-account")
def delete_account(body: DeleteAccountIn, response: Response,
                   user: User = Depends(current_user), db: Session = Depends(get_db)):
    """Permanently deletes the account and everything the user logged."""
    if is_admin(user):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "The admin account can't be deleted from the app")
    if not verify_password(body.password, user.hashed_password):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Password is wrong")
    delete_user_and_data(db, user)
    response.delete_cookie(COOKIE_NAME)
    return {"ok": True}


@router.post("/logout")
def logout(response: Response):
    response.delete_cookie(COOKIE_NAME)
    return {"ok": True}


@router.post("/consent")
def give_consent(user: User = Depends(current_user), db: Session = Depends(get_db)):
    """For accounts created before the consent notice (or after its wording changes)."""
    user.consent_at = utcnow()
    user.consent_version = CONSENT_VERSION
    db.commit()
    return user_to_dict(db, user)


@router.get("/me")
def me(user: User = Depends(current_user), db: Session = Depends(get_db)):
    return user_to_dict(db, user)
