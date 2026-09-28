"""Dashboard reads the database directly (never via the LLM)."""
from datetime import date

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import onboarded_user
from app.models import User
from app.services.analysis import range_summary, streaks
from app.services.logs import daily_summary
from app.timeutil import local_today

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


@router.get("/range")
def date_range(days: int = 7, user: User = Depends(onboarded_user), db: Session = Depends(get_db)):
    """Per-day totals and trend stats for the last `days` days (ending today)."""
    days = max(1, min(days, 90))
    return range_summary(db, user, local_today(user.timezone), days)


@router.get("/streaks")
def get_streaks(user: User = Depends(onboarded_user), db: Session = Depends(get_db)):
    """Meal-logging and target-achievement streaks for the Home tab."""
    return streaks(db, user, local_today(user.timezone))


@router.get("/daily")
def daily(day: date | None = None, user: User = Depends(onboarded_user), db: Session = Depends(get_db)):
    return daily_summary(db, user, day or local_today(user.timezone))
