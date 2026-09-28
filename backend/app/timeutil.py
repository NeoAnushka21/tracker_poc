"""Time-zone helpers. DB stores naive UTC; users think in local time."""
from datetime import date, datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from app.config import LEGACY_SNACK, MEAL_FALLBACK, MEAL_WINDOWS, SNACK_TYPES


def get_zone(tz_name: str) -> ZoneInfo:
    try:
        return ZoneInfo(tz_name)
    except (ZoneInfoNotFoundError, ValueError):
        return ZoneInfo("UTC")


def is_valid_timezone(tz_name: str) -> bool:
    try:
        ZoneInfo(tz_name)
        return True
    except (ZoneInfoNotFoundError, ValueError):
        return False


def utc_to_local(dt_utc: datetime, tz_name: str) -> datetime:
    return dt_utc.replace(tzinfo=timezone.utc).astimezone(get_zone(tz_name))


def local_to_utc(dt_local: datetime, tz_name: str) -> datetime:
    """Naive local datetime -> naive UTC datetime."""
    aware = dt_local.replace(tzinfo=get_zone(tz_name))
    return aware.astimezone(timezone.utc).replace(tzinfo=None)


def local_now(tz_name: str) -> datetime:
    return datetime.now(get_zone(tz_name))


def local_today(tz_name: str) -> date:
    return local_now(tz_name).date()


def local_day_bounds_utc(day: date, tz_name: str) -> tuple[datetime, datetime]:
    """[start, end) of a local calendar day, as naive UTC."""
    start = local_to_utc(datetime.combine(day, time.min), tz_name)
    end = local_to_utc(datetime.combine(day + timedelta(days=1), time.min), tz_name)
    return start, end


def infer_meal_type(local_dt: datetime) -> str:
    hour = local_dt.hour
    for meal, start, end in MEAL_WINDOWS:
        if start <= hour < end:
            return meal
    return MEAL_FALLBACK


def resolve_meal_type(stated: str | None, local_dt: datetime) -> str:
    """The user's stated meal wins. A plain 'snack' becomes morning or evening snack by time."""
    if stated == LEGACY_SNACK:
        inferred = infer_meal_type(local_dt)
        if inferred in SNACK_TYPES:
            return inferred
        return "morning_snack" if 5 <= local_dt.hour < 12 else "evening_snack"
    return stated or infer_meal_type(local_dt)
