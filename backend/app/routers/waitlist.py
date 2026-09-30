"""The welcome page's "Join the community" form (2026-10-01; see services/waitlist.py).

Public, no login. The always-on welcome site (config.LAUNCHER_ORIGIN) is another origin: main.py's
`waitlist_cors` answers its CORS checks for /api/waitlist only (no cookies involved).
"""
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request, Response, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app import config
from app.db import get_db
from app.models import User, WaitlistEntry, utcnow
from app.schemas import WaitlistJoinIn
from app.services import email, ratelimit
from app.services import waitlist as wl

router = APIRouter(prefix="/api/waitlist", tags=["waitlist"])

JOINED_REPLY = {"ok": True}   # the same reply whether or not the email was already on the list


@router.get("/options")
def options(response: Response):
    """What the welcome page's Join button does: "open" (Create account) or "waitlist" (the form)."""
    response.headers["Cache-Control"] = "no-store"
    return {"join_mode": config.JOIN_MODE}


@router.post("")
def join(body: WaitlistJoinIn, request: Request, background: BackgroundTasks, db: Session = Depends(get_db)):
    ratelimit.check_waitlist(request)
    if not body.consent:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "Please tick the box so we may email you about access")
    if body.website:                      # a bot filled in the hidden field: pretend it worked
        return JOINED_REPLY
    # Already on the list, or already has an account: nothing to add, and the reply doesn't say which.
    if wl.find(db, body.email) or db.scalars(select(User.id).where(User.email == body.email)).first():
        return JOINED_REPLY
    entry = WaitlistEntry(email=body.email, name=body.name, interest=body.interest, consent_at=utcnow())
    db.add(entry)
    try:
        db.commit()
    except IntegrityError:                # the same email sent twice at once
        db.rollback()
        return JOINED_REPLY
    waiting = db.scalar(select(func.count()).select_from(WaitlistEntry).where(WaitlistEntry.approved_at.is_(None)))
    if config.WAITLIST_ALERT_EMAIL:
        background.add_task(email.send, config.WAITLIST_ALERT_EMAIL,
                            f"{config.APP_NAME} waitlist: {entry.name} joined", wl.alert_text(entry, waiting or 0))
    return JOINED_REPLY
