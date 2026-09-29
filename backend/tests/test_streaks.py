"""Home tab streaks: consecutive days with a meal logged, and days with 85%+ of the protein target."""
from datetime import datetime, time, timedelta

from app.db import SessionLocal
from app.models import LogEntry, LogEntryItem, User
from app.services.analysis import _streak
from app.timeutil import local_day_bounds_utc, local_today


def test_streak_rule_today_in_progress():
    assert _streak([True, True, False]) == {"current": 2, "best": 2, "today_done": False}   # today not broken yet
    assert _streak([True, True, True]) == {"current": 3, "best": 3, "today_done": True}
    assert _streak([True, True, True, False, False, True, False])["current"] == 1
    assert _streak([True, True, True, False, True, False])["best"] == 3
    assert _streak([False, False])["current"] == 0


def _log(user_id: int, tz: str, days_ago: int, kcal: float, protein: float):
    day = local_today(tz) - timedelta(days=days_ago)
    start, _ = local_day_bounds_utc(day, tz)
    with SessionLocal() as db:
        e = LogEntry(user_id=user_id, eaten_at=start + timedelta(hours=12), meal_type="lunch")
        e.items.append(LogEntryItem(ingredient_name="meal", quantity=1, unit="plate", calories=kcal,
                                    protein_g=protein, carbs_g=0, fat_g=0, fiber_g=0))
        db.add(e)
        db.commit()


def test_streaks_endpoint(client, user):
    targets = user["targets"]
    with SessionLocal() as db:
        u = db.query(User).filter_by(email="me@example.com").one()
        uid, tz = u.id, u.timezone
    protein = targets["protein_g"]
    _log(uid, tz, 1, targets["calories"] * 2, protein)       # calories way over: still counts
    _log(uid, tz, 2, 500, protein * 0.85)                     # exactly 85% counts
    _log(uid, tz, 3, targets["calories"], protein * 0.9)
    _log(uid, tz, 4, targets["calories"], protein * 0.84)     # logged, protein just short
    _log(uid, tz, 6, targets["calories"], protein)

    s = client.get("/api/dashboard/streaks").json()
    assert s["logging"] == {"current": 4, "best": 4, "today_done": False}
    assert s["protein"] == {"current": 3, "best": 3, "today_done": False}
    assert s["rule"] == {"min_protein_pct": 85}
    assert len(s["last_7_days"]) == 7 and s["last_7_days"][-1]["logged"] is False
    assert [d["protein_hit"] for d in s["last_7_days"]] == [True, False, False, True, True, True, False]

    _log(uid, tz, 0, 300, protein * 0.5)                      # today logged, protein not there yet
    s = client.get("/api/dashboard/streaks").json()
    assert (s["logging"]["current"], s["protein"]["current"]) == (5, 3) and not s["protein"]["today_done"]

    _log(uid, tz, 0, 300, protein * 0.5)                      # today reaches 100%: extends it
    s = client.get("/api/dashboard/streaks").json()
    assert s["protein"] == {"current": 4, "best": 4, "today_done": True}
