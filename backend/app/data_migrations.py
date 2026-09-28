"""One-off data fixes run at startup. Each must be idempotent (safe to run every boot)."""
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import LEGACY_SNACK
from app.models import LogEntry, User
from app.timeutil import resolve_meal_type, utc_to_local


def relabel_legacy_snacks(db: Session) -> int:
    """Entries tagged 'snack' (before morning/evening snacks existed) get the snack
    type that matches the local time they were eaten."""
    rows = db.execute(
        select(LogEntry, User.timezone).join(User, User.id == LogEntry.user_id)
        .where(LogEntry.meal_type == LEGACY_SNACK)
    ).all()
    for entry, tz in rows:
        entry.meal_type = resolve_meal_type(LEGACY_SNACK, utc_to_local(entry.eaten_at, tz))
    db.commit()
    return len(rows)


def run_all(db: Session) -> None:
    relabel_legacy_snacks(db)
