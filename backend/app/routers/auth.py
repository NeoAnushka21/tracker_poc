from datetime import timedelta

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app import config
from app.config import CONSENT_TEXT, CONSENT_VERSION, COOKIE_SECURE, GOOGLE_CLIENT_ID, SESSION_DAYS
from app.db import get_db
from app.deps import current_user, is_admin
from app.models import User, utcnow
from app.routers.profile import user_to_dict
from app.google_auth import GoogleTokenError, verify_google_token
from app.schemas import (
    AdminLoginIn, Credentials, DeleteAccountIn, ForgotPasswordIn, GoogleLoginIn, PasswordChangeIn, RegisterIn, ResetPasswordIn,
)
from app.services import email, password_reset, ratelimit, totp, waitlist
from app.services.accounts import delete_user_and_data
from app.security import (
    COOKIE_NAME, burn_verify_time, create_session_token, hash_password, needs_rehash, verify_password,
)

router = APIRouter(prefix="/api/auth", tags=["auth"])


TOTP_REQUIRED = "code_required"   # the admin login screen then asks for the authenticator code


def _set_session_cookie(response: Response, user: User) -> None:
    lifetime = timedelta(hours=config.ADMIN_SESSION_HOURS) if is_admin(user) else timedelta(days=SESSION_DAYS)
    response.set_cookie(
        COOKIE_NAME,
        create_session_token(user.id, user.session_version or 0, lifetime),
        max_age=int(lifetime.total_seconds()),
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


@router.get("/options")
def options():
    """Sign-in options for the login screen (the Google button shows only when configured)."""
    return {"google_client_id": GOOGLE_CLIENT_ID or None, "password_reset": email.enabled(),
            "join_mode": config.JOIN_MODE}


@router.post("/register", status_code=status.HTTP_201_CREATED)
def register(body: RegisterIn, request: Request, response: Response, db: Session = Depends(get_db)):
    ratelimit.check_ip(request)
    if not body.consent:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "Please accept the data consent to create an account")
    if body.email in config.ADMIN_EMAILS:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "This email is reserved. Use Admin login.")
    if db.scalars(select(User).where(User.email == body.email)).first():
        raise HTTPException(status.HTTP_409_CONFLICT, "An account with this email already exists")
    waitlist.require_invite(db, body.email)
    user = User(email=body.email, hashed_password=hash_password(body.password),
                consent_at=utcnow(), consent_version=CONSENT_VERSION)
    _record_login(user)
    db.add(user)
    db.commit()
    _set_session_cookie(response, user)
    return user_to_dict(db, user)


@router.post("/login")
def login(body: Credentials, request: Request, response: Response, db: Session = Depends(get_db)):
    ratelimit.check_ip(request)
    user = _check_credentials(db, body)
    if is_admin(user):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "This is the admin account. Use Admin login.")
    _record_login(user)
    db.commit()
    _set_session_cookie(response, user)
    return user_to_dict(db, user)


@router.post("/admin-login")
def admin_login(body: AdminLoginIn, request: Request, response: Response, db: Session = Depends(get_db)):
    ratelimit.check_ip(request)
    user = _check_credentials(db, body)
    if not is_admin(user):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "This account isn't an admin. Use the regular login.")
    if totp.enabled(user):
        if not body.code:
            db.commit()                     # keep a password-hash upgrade, if any
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, TOTP_REQUIRED)
        if not totp.verify(user, body.code):
            ratelimit.record_login_failure(body.email)
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, "That code isn't right. Use the current code from your authenticator app.")
    _record_login(user)
    db.commit()
    _set_session_cookie(response, user)
    return user_to_dict(db, user)


def _check_credentials(db: Session, body: Credentials) -> User:
    """Wrong passwords are counted per email; after too many, that email is paused for a while."""
    ratelimit.check_login_failures(body.email)
    user = db.scalars(select(User).where(User.email == body.email)).first()
    if user is not None and not user.hashed_password:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED,
                            "This account signs in with Google. Use Continue with Google, then set a password "
                            "in Settings if you'd like one.")
    if user is None:
        burn_verify_time(body.password)   # an unknown email answers as slowly as a wrong password
    if user is None or not verify_password(body.password, user.hashed_password):
        ratelimit.record_login_failure(body.email)
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Wrong email or password")
    ratelimit.clear_login_failures(body.email)
    if needs_rehash(user.hashed_password):
        user.hashed_password = hash_password(body.password)   # upgrade old hashes; saved with the login
    return user


@router.post("/google")
def google_login(body: GoogleLoginIn, request: Request, response: Response, db: Session = Depends(get_db)):
    """Continue with Google. Returns {"status": "ok", "user"} with the session cookie set, or asks
    the browser to come back with the user's OK: "link_required" (an email+password account
    already uses this email) or "consent_required" (this would create a new account)."""
    if not GOOGLE_CLIENT_ID:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "Google sign-in isn't set up")
    ratelimit.check_ip(request)
    try:
        google = verify_google_token(body.credential)
    except GoogleTokenError as e:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, str(e)) from e
    if google["email"] in config.ADMIN_EMAILS:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "This is the admin account. Use Admin login.")

    user = db.scalars(select(User).where(User.google_sub == google["sub"])).first()
    if user is None:
        user = db.scalars(select(User).where(User.email == google["email"])).first()
        if user is not None:
            if user.google_sub:      # this email is linked to another Google account
                raise HTTPException(status.HTTP_409_CONFLICT, "This email is linked to a different Google account")
            if not body.link:
                return {"status": "link_required", "email": google["email"]}
            user.google_sub = google["sub"]
        else:
            waitlist.require_invite(db, google["email"])
            if not body.consent:
                return {"status": "consent_required", "email": google["email"]}
            user = User(email=google["email"], hashed_password="", google_sub=google["sub"],
                        preferred_name=google["name"], consent_at=utcnow(), consent_version=CONSENT_VERSION)
            db.add(user)
    _record_login(user)
    db.commit()
    _set_session_cookie(response, user)
    return {"status": "ok", "user": user_to_dict(db, user)}


FORGOT_REPLY = {"ok": True, "message": "If an account exists for that email, a reset link is on its way. "
                                          "It works for 30 minutes. Check your spam folder too."}


@router.post("/forgot-password")
def forgot_password(body: ForgotPasswordIn, request: Request, background: BackgroundTasks,
                    db: Session = Depends(get_db)):
    """Email a one-time reset link. The reply is the same whether or not the account exists, and the
    email is sent after the reply, so neither the wording nor the timing gives accounts away."""
    if not email.enabled():
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "Password reset by email isn't available yet")
    ratelimit.check_ip(request)
    ratelimit.check_reset_requests(body.email)
    user = db.scalars(select(User).where(User.email == body.email)).first()
    if user is not None and not is_admin(user):   # the admin account is recovered by the owner, not by email
        link = password_reset.create_link(db, user)
        db.commit()
        background.add_task(email.send, user.email, f"Reset your {config.APP_NAME} password",
                            password_reset.email_text(link))
    return FORGOT_REPLY


@router.post("/reset-password")
def reset_password(body: ResetPasswordIn, request: Request, db: Session = Depends(get_db)):
    ratelimit.check_ip(request)
    try:
        user = password_reset.use_link(db, body.token, body.new_password)
    except password_reset.ResetError as e:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(e)) from e
    db.commit()
    ratelimit.clear_login_failures(user.email)
    return {"ok": True}


@router.post("/change-password")
def change_password(body: PasswordChangeIn, response: Response, user: User = Depends(current_user),
                    db: Session = Depends(get_db)):
    if user.hashed_password and not verify_password(body.current_password, user.hashed_password):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Current password is wrong")
    user.hashed_password = hash_password(body.new_password)
    # A new password ends every other session; this browser gets a fresh cookie and stays in.
    user.session_version = (user.session_version or 0) + 1
    db.commit()
    _set_session_cookie(response, user)
    return {"ok": True}


@router.post("/delete-account")
def delete_account(body: DeleteAccountIn, response: Response,
                   user: User = Depends(current_user), db: Session = Depends(get_db)):
    """Permanently deletes the account and everything the user logged."""
    if is_admin(user):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "The admin account can't be deleted from the app")
    if user.hashed_password:
        if not verify_password(body.password, user.hashed_password):
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Password is wrong")
    elif body.confirm_email.strip().lower() != user.email:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Type your email exactly to confirm")
    delete_user_and_data(db, user)
    response.delete_cookie(COOKIE_NAME)
    return {"ok": True}


@router.post("/logout")
def logout(response: Response):
    response.delete_cookie(COOKIE_NAME)
    return {"ok": True}


@router.post("/logout-everywhere")
def logout_everywhere(response: Response, user: User = Depends(current_user), db: Session = Depends(get_db)):
    """End every session of this account, on all devices (including this one)."""
    user.session_version = (user.session_version or 0) + 1
    db.commit()
    response.delete_cookie(COOKIE_NAME)
    return {"ok": True}


@router.post("/consent")
def give_consent(user: User = Depends(current_user), db: Session = Depends(get_db)):
    """For accounts created before the consent notice (or after its wording changes)."""
    user.consent_at = utcnow()
    user.consent_version = CONSENT_VERSION
    db.commit()
    return user_to_dict(db, user)


@router.post("/guide-seen")
def guide_seen(user: User = Depends(current_user), db: Session = Depends(get_db)):
    """The first-run guide was finished or skipped; don't open it automatically again."""
    if user.guide_seen_at is None:
        user.guide_seen_at = utcnow()
        db.commit()
    return user_to_dict(db, user)


@router.get("/me")
def me(user: User = Depends(current_user), db: Session = Depends(get_db)):
    return user_to_dict(db, user)
