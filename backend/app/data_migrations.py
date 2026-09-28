"""One-off data fixes run at startup. Each must be idempotent (safe to run every boot)."""
from sqlalchemy import select
from sqlalchemy.orm import Session

from app import config
from app.config import CONSENT_VERSION, LEGACY_SNACK
from app.models import LogEntry, User, utcnow
from app.security import hash_password
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


def ensure_admin_accounts(db: Session) -> list[str]:
    """Create admin accounts that don't exist yet, using ADMIN_INITIAL_PASSWORD.
    Never changes an existing account's password."""
    if not config.ADMIN_INITIAL_PASSWORD:
        return []
    created = []
    for email in sorted(config.ADMIN_EMAILS):
        if db.scalars(select(User).where(User.email == email)).first() is None:
            db.add(User(email=email, hashed_password=hash_password(config.ADMIN_INITIAL_PASSWORD),
                        consent_at=utcnow(), consent_version=CONSENT_VERSION))
            created.append(email)
    db.commit()
    return created


def run_all(db: Session) -> None:
    relabel_legacy_snacks(db)
    ensure_admin_accounts(db)
