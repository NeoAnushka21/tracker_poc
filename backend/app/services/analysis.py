"""Trends over a date range for the Advanced analysis tab."""
from collections import defaultdict
from datetime import date, timedelta

from sqlalchemy.orm import Session

from app.config import ADHERENCE_CALORIE_TOLERANCE, ADHERENCE_MIN_PROTEIN_SHARE, KCAL_PER_G, MEAL_TYPES
from app.models import User, UserTarget
from app.services.logs import current_targets, current_weight, entries_between, sum_items, targets_to_dict
from app.services.water import water_between_range, water_target_ml
from app.timeutil import utc_to_local

MACROS = ("calories", "protein_g", "fiber_g", "carbs_g", "fat_g")


def on_target(consumed: dict, targets: dict | None) -> bool | None:
    """V1 adherence rule: calories within +/-10% and protein at least 90% of target."""
    if not targets or not targets["calories"]:
        return None
    kcal_ok = abs(consumed["calories"] - targets["calories"]) <= ADHERENCE_CALORIE_TOLERANCE * targets["calories"]
    protein_ok = consumed["protein_g"] >= ADHERENCE_MIN_PROTEIN_SHARE * targets["protein_g"]
    return kcal_ok and protein_ok


def _avg(values: list[float]) -> float | None:
    return round(sum(values) / len(values), 1) if values else None


def range_summary(db: Session, user: User, end: date, days: int) -> dict:
    start = end - timedelta(days=days - 1)
    entries = entries_between(db, user, start, end)
    items_by_day: dict[date, list] = defaultdict(list)
    kcal_by_meal: dict[str, float] = defaultdict(float)
    for e in entries:
        items_by_day[utc_to_local(e.eaten_at, user.timezone).date()].extend(e.items)
        kcal_by_meal[e.meal_type] += sum(i.calories for i in e.items)

    water_by_day: dict[date, float] = defaultdict(float)
    for w in water_between_range(db, user, start, end):
        water_by_day[utc_to_local(w.drank_at, user.timezone).date()] += w.amount_ml

    weight = current_weight(db, user.id)
    water_goal = water_target_ml(weight.weight_kg if weight else None, user.activity_level)

    out_days = []
    d = start
    while d <= end:
        items = items_by_day.get(d, [])
        consumed = sum_items(items)
        targets = targets_to_dict(current_targets(db, user.id, d))
        logged = bool(items)
        out_days.append({
            "date": d.isoformat(),
            "logged": logged,
            **{k: consumed[k] for k in MACROS},
            "water_ml": round(water_by_day.get(d, 0)),
            "targets": targets,
            "on_target": on_target(consumed, targets) if logged else None,
        })
        d += timedelta(days=1)

    logged_days = [x for x in out_days if x["logged"]]
    water_days = [x for x in out_days if x["water_ml"] > 0]
    total_macro_kcal = {
        "protein": sum(x["protein_g"] for x in logged_days) * KCAL_PER_G["protein"],
        "carbs": sum(x["carbs_g"] for x in logged_days) * KCAL_PER_G["carbs"],
        "fat": sum(x["fat_g"] for x in logged_days) * KCAL_PER_G["fat"],
    }
    macro_kcal_sum = sum(total_macro_kcal.values())
    return {
        "start": start.isoformat(),
        "end": end.isoformat(),
        "days": out_days,
        "water_target_ml": water_goal,
        "summary": {
            "days_in_range": days,
            "days_logged": len(logged_days),
            "days_on_target": sum(1 for x in logged_days if x["on_target"]),
            "avg": {**{k: _avg([x[k] for x in logged_days]) for k in MACROS},
                    "water_ml": _avg([x["water_ml"] for x in water_days])},
            "macro_split_pct": {
                k: round(v * 100 / macro_kcal_sum, 1) if macro_kcal_sum else None
                for k, v in total_macro_kcal.items()
            },
            "kcal_by_meal": {m: round(kcal_by_meal.get(m, 0)) for m in MEAL_TYPES},
            "adherence_rule": {
                "calorie_tolerance_pct": round(ADHERENCE_CALORIE_TOLERANCE * 100),
                "min_protein_pct": round(ADHERENCE_MIN_PROTEIN_SHARE * 100),
            },
        },
    }


# --- Streaks (Home tab) ------------------------------------------------------

STREAK_WINDOW_DAYS = 365


def _run_back(flags: list[bool]) -> int:
    """Consecutive True values counting back from the end of the list."""
    n = 0
    for f in reversed(flags):
        if not f:
            break
        n += 1
    return n


def _best_run(flags: list[bool]) -> int:
    best = run = 0
    for f in flags:
        run = run + 1 if f else 0
        best = max(best, run)
    return best


def _streak(flags: list[bool]) -> dict:
    """flags run oldest..today. Today is still in progress, so it only extends a streak once
    it qualifies; until then the streak counts up to yesterday and isn't broken."""
    today_done = flags[-1]
    current = _run_back(flags if today_done else flags[:-1])
    return {"current": current, "best": max(_best_run(flags), current), "today_done": today_done}


def streaks(db: Session, user: User, today: date) -> dict:
    """Two streaks: days with at least one confirmed meal, and days that met the target
    (same rule as Analysis: kcal within +/-10%, protein at least 90%)."""
    start = today - timedelta(days=STREAK_WINDOW_DAYS - 1)
    items_by_day: dict[date, list] = defaultdict(list)
    for e in entries_between(db, user, start, today):
        items_by_day[utc_to_local(e.eaten_at, user.timezone).date()].extend(e.items)

    all_targets = sorted(
        db.query(UserTarget).filter(UserTarget.user_id == user.id).all(),
        key=lambda t: (t.effective_date, t.id),
    )

    def targets_on(d: date) -> dict | None:
        chosen = None
        for t in all_targets:
            if t.effective_date <= d:
                chosen = t
        return targets_to_dict(chosen or (all_targets[0] if all_targets else None))

    logged, hit, last7 = [], [], []
    d = start
    while d <= today:
        items = items_by_day.get(d, [])
        ok = bool(items) and bool(on_target(sum_items(items), targets_on(d)))
        logged.append(bool(items))
        hit.append(ok)
        if (today - d).days < 7:
            last7.append({"date": d.isoformat(), "logged": bool(items), "on_target": ok})
        d += timedelta(days=1)

    return {
        "logging": _streak(logged),
        "target": _streak(hit),
        "last_7_days": last7,
        "rule": {
            "calorie_tolerance_pct": round(ADHERENCE_CALORIE_TOLERANCE * 100),
            "min_protein_pct": round(ADHERENCE_MIN_PROTEIN_SHARE * 100),
        },
    }
