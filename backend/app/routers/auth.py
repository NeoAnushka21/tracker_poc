from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import COOKIE_SECURE, SESSION_DAYS
from app.db import get_db
from app.deps import current_user
from app.models import User
from app.routers.profile import user_to_dict
from app.schemas import Credentials
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


@router.post("/register", status_code=status.HTTP_201_CREATED)
def register(body: Credentials, response: Response, db: Session = Depends(get_db)):
    if db.scalars(select(User).where(User.email == body.email)).first():
        raise HTTPException(status.HTTP_409_CONFLICT, "An account with this email already exists")
    user = User(email=body.email, hashed_password=hash_password(body.password))
    db.add(user)
    db.commit()
    _set_session_cookie(response, user.id)
    return user_to_dict(db, user)


@router.post("/login")
def login(body: Credentials, response: Response, db: Session = Depends(get_db)):
    user = db.scalars(select(User).where(User.email == body.email)).first()
    if user is None or not verify_password(body.password, user.hashed_password):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Wrong email or password")
    _set_session_cookie(response, user.id)
    return user_to_dict(db, user)


@router.post("/logout")
def logout(response: Response):
    response.delete_cookie(COOKIE_NAME)
    return {"ok": True}


@router.get("/me")
def me(user: User = Depends(current_user), db: Session = Depends(get_db)):
    return user_to_dict(db, user)
