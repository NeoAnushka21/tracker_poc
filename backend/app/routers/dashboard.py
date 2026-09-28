"""Dashboard reads the database directly (never via the LLM)."""
from datetime import date

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import onboarded_user
from app.models import User
from app.services.logs import daily_summary
from app.timeutil import local_today

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


@router.get("/daily")
def daily(day: date | None = None, user: User = Depends(onboarded_user), db: Session = Depends(get_db)):
    return daily_summary(db, user, day or local_today(user.timezone))
