"""'Day so far' summary + a motivational nudge, posted in chat after each confirmed log.

Template-based (no LLM call), so it's instant and doesn't use up the model's rate limit.
"""
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


def build_progress(db: Session, user: User) -> tuple[str, dict]:
    today = daily_summary(db, user, local_now(user.timezone).date())
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
        "calories": {"consumed": round(c["calories"]), "target": t["calories"] if t else None, "pct": kcal_pct},
        "macros": macros,
        "water": {"consumed_ml": w["consumed_ml"], "target_ml": w["target_ml"]},
        "meals_logged": len(today["entries"]),
        "headline": headline,
    }
    lines = [f"Day so far: {round(c['calories'])} kcal"
             + (f" of {t['calories']} ({kcal_pct}% of your daily budget)" if t else "")]
    lines += [f"- {m['label']}: {m['consumed']:g} g" + (f" of {m['target']} g ({m['pct']}%)" if m["target"] else "")
              for m in macros]
    lines.append(headline)
    return "\n".join(lines), data
