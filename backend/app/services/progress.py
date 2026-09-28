"""'Day so far' summary + a motivational nudge, posted in chat after each confirmed log.

Food logs get the calories-and-macros card; water logs get a water card. Both summarise the day
the log was for (a past day picked in the chat's date picker, or today).
Template-based (no LLM call), so it's instant and doesn't use up the model's rate limit.
"""
from datetime import date

from sqlalchemy.orm import Session

from app.models import User
from app.services.logs import daily_summary
from app.timeutil import local_now

MACROS = [("protein_g", "Protein"), ("fiber_g", "Fiber"), ("carbs_g", "Carbs"), ("fat_g", "Fat")]


def _pct(value: float, target: float | None) -> int | None:
    return round(value * 100 / target) if target else None


def motivation(kcal_pct: int | None, protein_pct: int | None, protein_left: float) -> str:
    if kcal_pct is not None and kcal_pct > 110:
        return ("You're past your calorie budget for today. No stress: keep the rest of the day light "
                "(water, veggies, lean protein). Tomorrow's a fresh start. 👍")
    if protein_pct is None:
        return "Logged! Stay consistent. 👍"
    if protein_pct >= 100:
        if kcal_pct is not None and kcal_pct >= 90:
            return "Protein goal smashed and calories right on target. That's a perfect day! 🔥👍"
        return "Protein goal smashed! 💪 Keep the rest of the day balanced. 👍"
    if protein_pct >= 75:
        return f"Almost there! Just {round(protein_left)} g protein to go. A little more! 👍"
    if protein_pct >= 50:
        return f"{protein_pct}% of your protein done, {100 - protein_pct}% to go. You can do it, stay consistent! 👍"
    if protein_pct >= 25:
        return "Good progress! Keep stacking protein through the day. 👍"
    return "It's just the start of your day, plenty of room to hit your goals. Stay consistent! 👍"


def water_motivation(pct: int | None, left_ml: float) -> str:
    if pct is None:
        return "Logged! Keep sipping through the day. 💧"
    if pct >= 100:
        return "Hydration goal reached! 💧 Great job, keep sipping when you're thirsty."
    if pct >= 75:
        return f"Almost there! Just {left_ml / 1000:.1f} L to go. 💧"
    if pct >= 50:
        return "Halfway there! Keep a bottle nearby. 💧"
    return "Good start! Sip steadily through the day to reach your goal. 💧"


def _day_fields(user: User, day: date | None) -> tuple[date, dict]:
    today = local_now(user.timezone).date()
    day = day or today
    return day, {"date": day.isoformat(), "is_today": day == today}


def build_water_progress(db: Session, user: User, day: date | None = None) -> tuple[str, dict]:
    day, fields = _day_fields(user, day)
    w = daily_summary(db, user, day)["water"]
    consumed, target = w["consumed_ml"], w["target_ml"]
    pct = _pct(consumed, target)
    left = max(0.0, (target or 0) - consumed)
    headline = water_motivation(pct, left)
    data = {"focus": "water", **fields, "water": {"consumed_ml": consumed, "target_ml": target, "pct": pct,
                                                  "logs": len(w["logs"])},
            "headline": headline}
    text = (f"Water {'today' if fields['is_today'] else 'on ' + day.strftime('%a %d %b')}: {consumed / 1000:.1f} L"
            + (f" of {target / 1000:.1f} L ({pct}%)" if target else "") + f"\n{headline}")
    return text, data


def build_progress(db: Session, user: User, day: date | None = None) -> tuple[str, dict]:
    day, fields = _day_fields(user, day)
    today = daily_summary(db, user, day)
    t, c, w = today["targets"], today["consumed"], today["water"]
    kcal_pct = _pct(c["calories"], t["calories"]) if t else None
    macros = [
        {"key": k, "label": label, "consumed": round(c[k], 1),
         "target": t[k] if t else None, "pct": _pct(c[k], t[k]) if t else None}
        for k, label in MACROS
    ]
    protein = macros[0]
    protein_left = max(0.0, (protein["target"] or 0) - protein["consumed"])
    headline = motivation(kcal_pct, protein["pct"], protein_left)
    data = {
        "focus": "macros",
        **fields,
        "calories": {"consumed": round(c["calories"]), "target": t["calories"] if t else None, "pct": kcal_pct},
        "macros": macros,
        "water": {"consumed_ml": w["consumed_ml"], "target_ml": w["target_ml"]},
        "meals_logged": len(today["entries"]),
        "headline": headline,
    }
    lines = [f"{'Day so far' if fields['is_today'] else day.strftime('%a %d %b')}: {round(c['calories'])} kcal"
             + (f" of {t['calories']} ({kcal_pct}% of your daily budget)" if t else "")]
    lines += [f"- {m['label']}: {m['consumed']:g} g" + (f" of {m['target']} g ({m['pct']}%)" if m["target"] else "")
              for m in macros]
    lines.append(headline)
    return "\n".join(lines), data
