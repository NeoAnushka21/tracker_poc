"""Read-side queries over confirmed log entries. Used by the dashboard and LLM tools."""
from datetime import date, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models import LogEntry, User, UserTarget, WeightLog
from app.nutrition import age_on, fiber_target_g, micronutrient_targets
from app.services import micros
from app.services.water import water_summary
from app.timeutil import local_day_bounds_utc, utc_to_local

NUTRIENTS = ["calories", "protein_g", "carbs_g", "fat_g", "fiber_g"]


def sum_items(items) -> dict:
    """Totals for a list of items (ORM objects or dicts)."""
    totals = {k: 0.0 for k in NUTRIENTS}
    for it in items:
        for k in NUTRIENTS:
            totals[k] += (it[k] if isinstance(it, dict) else getattr(it, k)) or 0
    return {k: round(v, 1) for k, v in totals.items()}


def item_to_dict(item) -> dict:
    return {
        "id": item.id,
        "ingredient_name": item.ingredient_name,
        "brand_name": item.brand_name,
        "quantity": item.quantity,
        "unit": item.unit,
        **{k: item_round(getattr(item, k)) for k in NUTRIENTS},
    }


def item_round(v: float | None) -> float:
    return round(v or 0, 1)


def entry_to_dict(entry: LogEntry, tz_name: str) -> dict:
    local = utc_to_local(entry.eaten_at, tz_name)
    return {
        "id": entry.id,
        "eaten_at": local.strftime("%Y-%m-%dT%H:%M"),
        "meal_type": entry.meal_type,
        "items": [item_to_dict(i) for i in entry.items],
        "totals": sum_items(entry.items),
    }


def get_active_entry(db: Session, user_id: int, entry_id: int) -> LogEntry | None:
    entry = db.get(LogEntry, entry_id)
    if entry is None or entry.user_id != user_id or entry.deleted_at is not None:
        return None
    return entry


def entries_between(db: Session, user: User, start_day: date, end_day: date) -> list[LogEntry]:
    """Confirmed, non-deleted entries for local days start_day..end_day inclusive."""
    start_utc, _ = local_day_bounds_utc(start_day, user.timezone)
    _, end_utc = local_day_bounds_utc(end_day, user.timezone)
    stmt = (
        select(LogEntry)
        .where(
            LogEntry.user_id == user.id,
            LogEntry.deleted_at.is_(None),
            LogEntry.eaten_at >= start_utc,
            LogEntry.eaten_at < end_utc,
        )
        .options(selectinload(LogEntry.items))
        .order_by(LogEntry.eaten_at)
    )
    return list(db.scalars(stmt))


def current_targets(db: Session, user_id: int, on_day: date | None = None) -> UserTarget | None:
    stmt = select(UserTarget).where(UserTarget.user_id == user_id)
    if on_day is not None:
        stmt = stmt.where(UserTarget.effective_date <= on_day)
    stmt = stmt.order_by(UserTarget.effective_date.desc(), UserTarget.id.desc()).limit(1)
    target = db.scalars(stmt).first()
    if target is None and on_day is not None:
        # Day is before the first target was set: fall back to the earliest one.
        target = db.scalars(
            select(UserTarget).where(UserTarget.user_id == user_id)
            .order_by(UserTarget.effective_date, UserTarget.id).limit(1)
        ).first()
    return target


def current_weight(db: Session, user_id: int) -> WeightLog | None:
    stmt = (
        select(WeightLog).where(WeightLog.user_id == user_id)
        .order_by(WeightLog.logged_at.desc(), WeightLog.id.desc()).limit(1)
    )
    return db.scalars(stmt).first()


def targets_to_dict(t: UserTarget | None) -> dict | None:
    if t is None:
        return None
    return {
        "calories": t.daily_calorie_target,
        "protein_g": t.protein_target_g,
        "carbs_g": t.carbs_target_g,
        "fat_g": t.fat_target_g,
        "fiber_g": fiber_target_g(t.daily_calorie_target),
        "effective_date": t.effective_date.isoformat(),
        "is_custom": t.is_custom,
    }


def daily_summary(db: Session, user: User, day: date) -> dict:
    entries = entries_between(db, user, day, day)
    all_items = [it for e in entries for it in e.items]
    consumed = sum_items(all_items)
    targets = targets_to_dict(current_targets(db, user.id, day))
    remaining = None
    if targets:
        remaining = {
            k: round(targets[k] - consumed[k], 1)
            for k in ("calories", "protein_g", "carbs_g", "fat_g", "fiber_g")
        }
    return {
        "date": day.isoformat(),
        "targets": targets,
        "consumed": consumed,
        "remaining": remaining,
        "micronutrients": _micros_summary(user, day, all_items),
        "water": water_summary(db, user, day, _weight(db, user.id)),
        "entries": [entry_to_dict(e, user.timezone) for e in entries],
    }


def _weight(db: Session, user_id: int) -> float | None:
    w = current_weight(db, user_id)
    return w.weight_kg if w else None


def _micros_summary(user: User, day: date, items) -> dict:
    """Consumed vs reference value per micronutrient, plus how many items had estimates."""
    consumed = micros.total(it.micronutrients for it in items)
    age = age_on(user.date_of_birth, day) if user.date_of_birth else None
    return {
        "items_total": len(items),
        "items_with_data": sum(1 for it in items if it.micronutrients),
        "nutrients": [
            {**t, "consumed": round(consumed.get(t["key"], 0), 1)}
            for t in micronutrient_targets(user.sex, age)
        ],
    }


def logs_by_day(db: Session, user: User, start_day: date, end_day: date) -> list[dict]:
    entries = entries_between(db, user, start_day, end_day)
    days: dict[str, list[dict]] = {}
    d = start_day
    while d <= end_day:
        days[d.isoformat()] = []
        d += timedelta(days=1)
    for e in entries:
        ed = entry_to_dict(e, user.timezone)
        days.setdefault(ed["eaten_at"][:10], []).append(ed)
    return [
        {
            "date": day,
            "entries": day_entries,
            "totals": sum_items([it for e in day_entries for it in e["items"]]),
        }
        for day, day_entries in days.items()
    ]
