"""The waitlist (2026-10-01): "Join the community" sign-ups while config.JOIN_MODE is "waitlist",
and the gate that lets only approved emails create an account.

Existing accounts are never affected: the gate is checked only where a new account would be made
(email sign-up and a first "Continue with Google").
"""
from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app import config
from app.models import WaitlistEntry

NOT_INVITED = (f"{config.APP_NAME} is invite-only for now. Join the waitlist on the welcome page and "
               "we'll email you an invitation as soon as there's a spot. Invited? Use the email address we wrote to.")


def find(db: Session, email: str) -> WaitlistEntry | None:
    return db.scalars(select(WaitlistEntry).where(WaitlistEntry.email == email)).first()


def may_create_account(db: Session, email: str) -> bool:
    if config.JOIN_MODE == "open":
        return True
    entry = find(db, email)
    return entry is not None and entry.approved_at is not None


def require_invite(db: Session, email: str) -> None:
    """Raise 403 unless this email may create a new account."""
    if not may_create_account(db, email):
        raise HTTPException(status.HTTP_403_FORBIDDEN, NOT_INVITED)


def signup_link() -> str:
    """Where an invited person creates their account. The always-on welcome site forwards #signup to
    the app once it's awake, so they never see the free server's waking page."""
    return f"{config.LAUNCHER_ORIGIN or config.PUBLIC_APP_URL}/#signup"


def alert_text(entry: WaitlistEntry, waiting: int) -> str:
    return (
        f"{entry.name} <{entry.email}> joined the {config.APP_NAME} waitlist.\n\n"
        f"What they'd like to track: {entry.interest or '(not given)'}\n\n"
        f"People waiting now: {waiting}\n"
        f"Review and approve them in the admin console (Admin → Waitlist): {config.PUBLIC_APP_URL}\n"
    )


def invite_text(entry: WaitlistEntry) -> str:
    return (
        f"Hi {entry.name},\n\n"
        f"Good news: there's a spot for you in {config.APP_NAME}, the AI meal & wellness tracker.\n\n"
        f"Create your account here, with this email address ({entry.email}) or Continue with Google "
        f"using the same address:\n{signup_link()}\n\n"
        "The first time, the app can take up to a minute to wake up.\n\n"
        "Thanks for joining early. Reply to this email any time with questions or feedback.\n\n"
        f"The {config.APP_NAME} team\n"
    )
