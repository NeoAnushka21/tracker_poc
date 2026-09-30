"""Optional "about you" answers: diet, allergies, pace, meal times, training, health.

All optional and skippable (asked after the required profile, and editable in Settings). Each
answer is used, never only stored (data minimisation):
- diet, allergies, training, health conditions, pregnancy -> MacBro's context (`prompt_lines`)
- allergies -> a heads-up on cards whose foods likely contain one (`allergen_note`)
- pace, pregnancy/breastfeeding -> the calculated targets (`target_options`)
- meal times -> which meal a time counts as (`meal_times`, timeutil.meal_windows) and the
  Dashboard's default time for a meal
"""
import re

from sqlalchemy.orm import Session

from app.config import (
    ALLERGENS, DIET_TYPES, GOAL_SETTINGS, HEALTH_CONDITIONS, PACE_OPTIONS, PREGNANCY_STATES, TRAINING_TYPES,
)
from app.models import User, UserPreferences, utcnow

WEEKDAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
_TIME = re.compile(r"^([01]\d|2[0-3]):([0-5]\d)$")


def options() -> dict:
    """The choices for the form (labels included), so the lists live in one place (config)."""
    return {
        "diet_types": DIET_TYPES,
        "allergens": {k: label for k, (label, _) in ALLERGENS.items()},
        "pace": PACE_OPTIONS,
        "training_types": TRAINING_TYPES,
        "weekdays": WEEKDAYS,
        "health_conditions": HEALTH_CONDITIONS,
        "pregnancy": PREGNANCY_STATES,
    }


def to_dict(p: UserPreferences | None) -> dict:
    fields = ("diet_type", "allergies", "allergy_notes", "pace_kg_per_week", "breakfast_time", "lunch_time",
              "dinner_time", "training_days", "training_type", "health_conditions", "pregnancy")
    out = {f: getattr(p, f, None) for f in fields}
    for f in ("allergies", "training_days", "health_conditions"):
        out[f] = out[f] or []
    out["health_consent"] = bool(p and p.health_consent_at)
    out["answered"] = p is not None
    return out


def _hours(t: str | None) -> float | None:
    return int(t[:2]) + int(t[3:]) / 60 if t else None


def check(user: User, data: dict) -> dict:
    """Cleaned answers, or ValueError with a message for the user. Empty values are allowed."""
    def one_of(key, allowed):
        v = data.get(key) or None
        if v is not None and v not in allowed:
            raise ValueError(f"Unknown choice for {key.replace('_', ' ')}")
        return v

    def some_of(key, allowed):
        v = list(dict.fromkeys(data.get(key) or []))
        if any(x not in allowed for x in v):
            raise ValueError(f"Unknown choice for {key.replace('_', ' ')}")
        return v or None

    out = {
        "diet_type": one_of("diet_type", DIET_TYPES),
        "allergies": some_of("allergies", ALLERGENS),
        "allergy_notes": (data.get("allergy_notes") or "").strip()[:200] or None,
        "training_days": sorted(some_of("training_days", range(7)) or []) or None,
        "training_type": one_of("training_type", TRAINING_TYPES),
        "health_conditions": some_of("health_conditions", HEALTH_CONDITIONS),
        "pregnancy": one_of("pregnancy", PREGNANCY_STATES),
    }
    pace = data.get("pace_kg_per_week") or None
    allowed = {p for ps in PACE_OPTIONS.values() for p in ps}
    if pace is not None and pace not in allowed:
        raise ValueError("Pick a pace from the list")
    out["pace_kg_per_week"] = pace
    for meal in ("breakfast", "lunch", "dinner"):
        t = (data.get(f"{meal}_time") or "").strip() or None
        if t is not None and not _TIME.match(t):
            raise ValueError(f"Use HH:MM for the {meal} time")
        out[f"{meal}_time"] = t
    times = [_hours(out[f"{m}_time"]) for m in ("breakfast", "lunch", "dinner")]
    given = [t for t in times if t is not None]
    if any(b - a < 2 for a, b in zip(given, given[1:])):
        raise ValueError("Meal times should be in order (breakfast, lunch, dinner) and at least 2 hours apart")
    if out["pregnancy"] and user.sex != "female":
        raise ValueError("Pregnancy and breastfeeding only apply to a female profile")
    if (out["health_conditions"] or out["pregnancy"]) and not data.get("health_consent"):
        raise ValueError("To save health details, tick the box to agree they're used to tailor your targets and MacBro")
    return out


def save(db: Session, user: User, data: dict) -> UserPreferences:
    cleaned = check(user, data)
    p = user.preferences or UserPreferences(user_id=user.id)
    for k, v in cleaned.items():
        setattr(p, k, v)
    if cleaned["health_conditions"] or cleaned["pregnancy"]:
        p.health_consent_at = p.health_consent_at or utcnow()
    else:
        p.health_consent_at = None          # nothing sensitive stored, so no consent needed
    p.skipped_at = None
    p.updated_at = utcnow()
    if user.preferences is None:
        db.add(p)
        user.preferences = p
    db.flush()
    return p


def skip(db: Session, user: User) -> None:
    """Skip for now: don't ask again (everything stays editable in Settings)."""
    if user.preferences is None:
        user.preferences = UserPreferences(user_id=user.id, skipped_at=utcnow(), updated_at=utcnow())
        db.add(user.preferences)
        db.flush()


# --- where the answers are used -----------------------------------------------------------------

def target_options(user: User) -> dict:
    """Extra inputs for calculate_targets: the chosen pace, and no deficit while pregnant or
    breastfeeding (safety; their extra needs are for a doctor or dietitian to set)."""
    p = user.preferences
    if p is None:
        return {}
    pace = p.pace_kg_per_week if p.pace_kg_per_week in PACE_OPTIONS.get(user.goal_type or "", []) else None
    return {"pace_kg_per_week": pace, "no_deficit": p.pregnancy is not None}


def meal_times(user: User) -> dict[str, float] | None:
    """{"breakfast": 8.5, ...} hours of the day the user usually eats, when given."""
    p = user.preferences
    if p is None:
        return None
    times = {m: _hours(getattr(p, f"{m}_time")) for m in ("breakfast", "lunch", "dinner")}
    return {m: h for m, h in times.items() if h is not None} or None


def prompt_lines(user: User) -> list[str]:
    """Short facts for MacBro's context (only what the user chose to share)."""
    p = user.preferences
    if p is None:
        return []
    lines = []
    if p.diet_type:
        lines.append(f"Diet: {DIET_TYPES[p.diet_type]}")
    allergies = [ALLERGENS[a][0] for a in p.allergies or []] + ([p.allergy_notes] if p.allergy_notes else [])
    if allergies:
        lines.append(f"Allergies / intolerances: {', '.join(allergies)}")
    if p.pace_kg_per_week:
        lines.append(f"Chosen pace: {p.pace_kg_per_week:g} kg per week")
    if p.training_days or p.training_type:
        days = ", ".join(WEEKDAYS[d] for d in p.training_days or [])
        kind = TRAINING_TYPES.get(p.training_type or "", "")
        lines.append("Trains: " + " · ".join(x for x in (kind, days) if x))
    times = [f"{m} {getattr(p, f'{m}_time')}" for m in ("breakfast", "lunch", "dinner") if getattr(p, f"{m}_time")]
    if times:
        lines.append("Usual meal times: " + ", ".join(times))
    if p.health_consent_at and p.health_conditions:
        lines.append("Health conditions (shared by the user): " + ", ".join(HEALTH_CONDITIONS[c] for c in p.health_conditions))
    if p.health_consent_at and p.pregnancy:
        lines.append(f"Currently: {PREGNANCY_STATES[p.pregnancy].lower()}")
    return lines


def allergen_note(user: User, food_names: list[str]) -> str | None:
    """'Heads-up: paneer usually contains milk / dairy (lactose), which you listed.' or None."""
    p = user.preferences
    if p is None or not p.allergies:
        return None
    hits = []
    for name in food_names:
        low = name.lower()
        for key in p.allergies:
            label, words = ALLERGENS[key]
            if any(re.search(rf"\b{re.escape(w)}\b", low) for w in words):
                hits.append(f"{name} usually contains {label.split(' (')[0].lower()}")
                break
    if not hits:
        return None
    return "Heads-up: " + "; ".join(hits) + ", which you listed as an allergy or intolerance."


assert set(PACE_OPTIONS) <= set(GOAL_SETTINGS)
