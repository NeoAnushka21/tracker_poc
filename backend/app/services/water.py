"""Water tracker: a daily target from body weight + activity, and logged amounts."""
from datetime import date, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import WATER_ACTIVITY_EXTRA_ML, WATER_ML_PER_KG
from app.models import User, WaterLog, utcnow
from app.timeutil import local_day_bounds_utc, utc_to_local


def water_target_ml(weight_kg: float | None, activity_level: str | None) -> int | None:
    """35 ml per kg body weight plus extra for activity, rounded to 50 ml."""
    if not weight_kg:
        return None
    ml = weight_kg * WATER_ML_PER_KG + WATER_ACTIVITY_EXTRA_ML.get(activity_level or "", 0)
    return int(round(ml / 50) * 50)


def add_water(db: Session, user: User, amount_ml: float, drank_at: datetime | None = None) -> WaterLog:
    log = WaterLog(user_id=user.id, amount_ml=round(amount_ml), drank_at=drank_at or utcnow())
    db.add(log)
    db.flush()
    return log


def water_between_range(db: Session, user: User, start_day: date, end_day: date) -> list[WaterLog]:
    start, _ = local_day_bounds_utc(start_day, user.timezone)
    _, end = local_day_bounds_utc(end_day, user.timezone)
    stmt = (
        select(WaterLog)
        .where(WaterLog.user_id == user.id, WaterLog.drank_at >= start, WaterLog.drank_at < end)
        .order_by(WaterLog.drank_at, WaterLog.id)
    )
    return list(db.scalars(stmt))


def water_summary(db: Session, user: User, day: date, weight_kg: float | None) -> dict:
    logs = water_between_range(db, user, day, day)
    return {
        "target_ml": water_target_ml(weight_kg, user.activity_level),
        "consumed_ml": round(sum(w.amount_ml for w in logs)),
        "logs": [
            {"id": w.id, "amount_ml": w.amount_ml,
             "drank_at": utc_to_local(w.drank_at, user.timezone).strftime("%Y-%m-%dT%H:%M")}
            for w in logs
        ],
    }
