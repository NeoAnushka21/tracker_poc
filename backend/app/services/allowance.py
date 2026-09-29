"""Daily AI allowance: how many AI-answered requests a user has left today (local day)."""
from datetime import timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app import config
from app.models import AiRequest, User
from app.timeutil import local_day_bounds_utc, local_today


class AllowanceExceeded(Exception):
    """The user has used today's AI allowance. The message is shown to them."""


def status(db: Session, user: User) -> dict:
    """{limit, used, remaining, resets_at}; limit and remaining are None when unlimited."""
    limit = config.AI_DAILY_MESSAGE_LIMIT
    start, end = local_day_bounds_utc(local_today(user.timezone), user.timezone)
    used = db.scalar(select(func.count()).select_from(AiRequest).where(
        AiRequest.user_id == user.id, AiRequest.created_at >= start, AiRequest.created_at < end)) or 0
    return {
        "limit": limit or None,
        "used": used,
        "remaining": max(0, limit - used) if limit else None,
        "resets_at": end.isoformat() + "Z",
    }


def check(db: Session, user: User) -> None:
    """Raise AllowanceExceeded before an AI call if today's allowance is used up."""
    s = status(db, user)
    if s["remaining"] == 0:
        raise AllowanceExceeded(
            f"You've used all {s['limit']} AI messages for today. They reset at midnight. Until then, "
            "saved foods, quick replies (water, today's summary), the Dashboard and all buttons still work."
        )


def record(db: Session, user: User, kind: str) -> None:
    """Count one AI-answered request (commit it together with the reply)."""
    db.add(AiRequest(user_id=user.id, kind=kind))
