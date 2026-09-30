from fastapi import APIRouter, Depends, HTTPException, Response, status
from fastapi.responses import JSONResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app import config
from app.db import get_db
from app.config import CONSENT_VERSION
from app.deps import current_user, is_admin, onboarded_user
from app.config import BODY_PARTS, BODY_PART_KEYS
from app.models import BodyMeasurement, User, UserTarget, WeightLog
from app.nutrition import age_on, calculate_targets
from app.schemas import HeightIn, LocationIn, MeasurementsIn, OnboardingIn, TargetsIn, WeightIn
from app.services import places, preferences
from app.services.export import export_user_data
from app.services.body import SAME_SESSION_DAYS, bmi, body_fat_navy
from app.services.logs import current_targets, current_weight, targets_to_dict
from app.timeutil import is_valid_timezone, local_today

router = APIRouter(prefix="/api/profile", tags=["profile"])


def user_to_dict(db: Session, user: User) -> dict:
    weight = current_weight(db, user.id)
    return {
        "id": str(user.public_id),
        "email": user.email,
        "onboarded": user.onboarded,
        "preferred_name": user.preferred_name,
        "date_of_birth": user.date_of_birth.isoformat() if user.date_of_birth else None,
        "sex": user.sex,
        "height_cm": user.height_cm,
        "weight_kg": weight.weight_kg if weight else None,
        "unit_system": user.unit_system,
        "timezone": user.timezone,
        "country": user.country,
        "country_name": places.country_name(user.country),
        "region": user.region,
        # Accounts from before country was asked: shown a one-time "where do you live?" screen.
        "needs_location": user.country is None and user.onboarded and not is_admin(user),
        # Optional "about you" questions: offered once (answered or skipped), then only in Settings.
        "needs_preferences": user.preferences is None and user.onboarded and not is_admin(user),
        "age": age_on(user.date_of_birth, local_today(user.timezone)) if user.date_of_birth else None,
        "goal_type": user.goal_type,
        "activity_level": user.activity_level,
        "targets": targets_to_dict(current_targets(db, user.id)),
        "consented": user.consent_version == CONSENT_VERSION,
        "is_admin": is_admin(user),
        "created_at": user.created_at.isoformat() + "Z" if user.created_at else None,
        "last_login_at": user.last_login_at.isoformat() + "Z" if user.last_login_at else None,
        "consented_at": user.consent_at.isoformat() + "Z" if user.consent_at else None,
        "guide_seen": user.guide_seen_at is not None,
        "has_password": bool(user.hashed_password),
        "google_linked": user.google_sub is not None,
    }


def _calculated_targets(user: User, weight_kg: float):
    return calculate_targets(
        weight_kg=weight_kg,
        height_cm=user.height_cm,
        age=age_on(user.date_of_birth, local_today(user.timezone)),
        sex=user.sex,
        activity_level=user.activity_level,
        goal_type=user.goal_type,
        **preferences.target_options(user),
    )


def _save_calculated_targets(db: Session, user: User, weight_kg: float) -> dict:
    t = _calculated_targets(user, weight_kg)
    db.add(UserTarget(
        user_id=user.id,
        daily_calorie_target=t.daily_calorie_target,
        protein_target_g=t.protein_target_g,
        carbs_target_g=t.carbs_target_g,
        fat_target_g=t.fat_target_g,
        effective_date=local_today(user.timezone),
    ))
    return {"bmr": t.bmr, "tdee": t.tdee}


@router.get("/export")
def export_data(user: User = Depends(current_user), db: Session = Depends(get_db)):
    """Download my data: everything stored about this account, as a JSON file."""
    filename = f"{config.APP_NAME.lower()}-my-data-{local_today(user.timezone).isoformat()}.json"
    return JSONResponse(export_user_data(db, user),
                        headers={"Content-Disposition": f'attachment; filename="{filename}"',
                                 "Cache-Control": "no-store"})


@router.post("/onboarding")
def onboarding(body: OnboardingIn, user: User = Depends(current_user), db: Session = Depends(get_db)):
    if not is_valid_timezone(body.timezone):
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, f"Unknown time zone '{body.timezone}'")
    age = age_on(body.date_of_birth, local_today(body.timezone))
    if body.date_of_birth > local_today(body.timezone) or age > config.MAX_USER_AGE:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "Please check your date of birth")
    if age < config.MIN_USER_AGE:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT,
                            f"{config.APP_NAME} is for adults ({config.MIN_USER_AGE} and over), so we can't set up "
                            "your profile. You can delete this account in Settings.")
    try:
        user.country, user.region = places.check(body.country, body.region)
    except ValueError as e:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, str(e)) from e
    for field in ("preferred_name", "date_of_birth", "sex", "height_cm", "unit_system",
                  "timezone", "goal_type", "activity_level"):
        setattr(user, field, getattr(body, field))
    if user.preferred_name is not None:
        user.preferred_name = user.preferred_name.strip() or None

    db.add(WeightLog(user_id=user.id, weight_kg=body.weight_kg))
    calc = _save_calculated_targets(db, user, body.weight_kg)
    db.commit()
    return {**user_to_dict(db, user), "calculation": calc}


@router.get("/countries")
def countries(response: Response):
    """Countries and their regions for the dropdowns. Public reference data (no login needed)."""
    response.headers["Cache-Control"] = "public, max-age=86400"
    return places.countries()


@router.put("/location")
def set_location(body: LocationIn, user: User = Depends(current_user), db: Session = Depends(get_db)):
    """Country (required) and region (optional), from the dropdowns: onboarding for accounts from
    before they were asked, and Settings."""
    try:
        user.country, user.region = places.check(body.country, body.region)
    except ValueError as e:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, str(e)) from e
    db.commit()
    return user_to_dict(db, user)


@router.get("/preferences")
def get_preferences(user: User = Depends(current_user)):
    """The optional "about you" answers, and the choices for each question."""
    return {"preferences": preferences.to_dict(user.preferences), "options": preferences.options()}


@router.put("/preferences")
def save_preferences(body: dict, user: User = Depends(current_user), db: Session = Depends(get_db)):
    """Save the optional answers (any subset; empty = not answered). When they change the calculated
    targets (pace, pregnancy), `suggested_targets` is returned so the UI can offer to use them."""
    try:
        preferences.save(db, user, body)
    except ValueError as e:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, str(e)) from e
    db.commit()
    out = {"user": user_to_dict(db, user), "preferences": preferences.to_dict(user.preferences),
           "suggested_targets": None}
    weight, current = current_weight(db, user.id), current_targets(db, user.id)
    if user.onboarded and weight and current:
        t = _calculated_targets(user, weight.weight_kg)
        if abs(t.daily_calorie_target - current.daily_calorie_target) >= 50:
            out["suggested_targets"] = t.__dict__
    return out


@router.post("/recalculate-targets")
def recalculate_targets(user: User = Depends(onboarded_user), db: Session = Depends(get_db)):
    """Replace the targets with the formula's (incl. pace and pregnancy): after the optional
    questions in onboarding, and when the user accepts `suggested_targets`."""
    weight = current_weight(db, user.id)
    if weight is None:
        raise HTTPException(status.HTTP_409_CONFLICT, "Log your weight first")
    calc = _save_calculated_targets(db, user, weight.weight_kg)
    db.commit()
    return {**user_to_dict(db, user), "calculation": calc}


@router.post("/preferences/skip")
def skip_preferences(user: User = Depends(current_user), db: Session = Depends(get_db)):
    """Skip the optional questions for now; they stay in Settings."""
    preferences.skip(db, user)
    db.commit()
    return user_to_dict(db, user)


@router.put("/targets")
def update_targets(body: TargetsIn, user: User = Depends(onboarded_user), db: Session = Depends(get_db)):
    db.add(UserTarget(
        user_id=user.id,
        daily_calorie_target=body.daily_calorie_target,
        protein_target_g=body.protein_target_g,
        carbs_target_g=body.carbs_target_g,
        fat_target_g=body.fat_target_g,
        effective_date=local_today(user.timezone),
        is_custom=True,
    ))
    db.commit()
    return user_to_dict(db, user)


@router.post("/weight")
def log_weight(body: WeightIn, user: User = Depends(onboarded_user), db: Session = Depends(get_db)):
    db.add(WeightLog(user_id=user.id, weight_kg=body.weight_kg))
    if body.recalculate_targets:
        _save_calculated_targets(db, user, body.weight_kg)
    db.commit()
    return user_to_dict(db, user)


@router.get("/preview-targets")
def preview_targets(user: User = Depends(onboarded_user), db: Session = Depends(get_db)):
    """What the formula would give now (used to show 'reset to calculated' in the UI)."""
    weight = current_weight(db, user.id)
    t = _calculated_targets(user, weight.weight_kg)
    return t.__dict__


# --- Body profile --------------------------------------------------------------

def _iso(dt) -> str:
    return dt.isoformat() + "Z"


def body_profile(db: Session, user: User) -> dict:
    weights = list(db.scalars(
        select(WeightLog).where(WeightLog.user_id == user.id).order_by(WeightLog.logged_at.desc(), WeightLog.id.desc())
    ))
    sets = list(db.scalars(
        select(BodyMeasurement).where(BodyMeasurement.user_id == user.id)
        .order_by(BodyMeasurement.measured_at.desc(), BodyMeasurement.id.desc())
    ))
    latest, when = [], {}
    for key, label, tip in BODY_PARTS:
        values = [(m.measured_at, getattr(m, key)) for m in sets if getattr(m, key) is not None]
        current = values[0] if values else None
        previous = values[1] if len(values) > 1 else None
        if current:
            when[key] = current[0]
        latest.append({
            "key": key, "label": label, "tip": tip,
            "value_cm": current[1] if current else None,
            "measured_at": _iso(current[0]) if current else None,
            "change_cm": round(current[1] - previous[1], 1) if current and previous else None,
        })
    now = {p["key"]: p["value_cm"] for p in latest}
    weight_kg = weights[0].weight_kg if weights else None
    fat = body_fat_navy(user.sex, user.height_cm, now["neck_cm"], now["waist_cm"], now["hips_cm"])
    if fat["status"] == "ok":
        used = [when[k] for k in ("neck_cm", "waist_cm", "hips_cm") if k in when and (k != "hips_cm" or user.sex == "female")]
        if (max(used) - min(used)).days > SAME_SESSION_DAYS:
            fat["warning"] = "These measurements were taken more than a month apart; re-measure them together for a better estimate."
    return {
        "sex": user.sex,
        "height_cm": user.height_cm,
        "weight_kg": weight_kg,
        "bmi": bmi(weight_kg, user.height_cm),
        "body_fat": fat,
        "weight_history": [{"weight_kg": w.weight_kg, "logged_at": _iso(w.logged_at)} for w in weights[:10]],
        "latest": latest,
        "history": [
            {"id": m.id, "measured_at": _iso(m.measured_at),
             **{k: getattr(m, k) for k in BODY_PART_KEYS}}
            for m in sets[:20]
        ],
    }


@router.get("/body")
def get_body(user: User = Depends(onboarded_user), db: Session = Depends(get_db)):
    return body_profile(db, user)


@router.post("/height")
def update_height(body: HeightIn, user: User = Depends(onboarded_user), db: Session = Depends(get_db)):
    user.height_cm = body.height_cm
    if body.recalculate_targets:
        weight = current_weight(db, user.id)
        if weight:
            _save_calculated_targets(db, user, weight.weight_kg)
    db.commit()
    return user_to_dict(db, user)


@router.post("/measurements", status_code=status.HTTP_201_CREATED)
def add_measurements(body: MeasurementsIn, user: User = Depends(onboarded_user), db: Session = Depends(get_db)):
    values = {k: round(v, 1) for k, v in body.model_dump().items() if v is not None}
    if not values:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "Enter at least one measurement")
    db.add(BodyMeasurement(user_id=user.id, **values))
    db.commit()
    return body_profile(db, user)


@router.put("/measurements/{measurement_id}")
def edit_measurement(measurement_id: int, body: MeasurementsIn, user: User = Depends(onboarded_user),
                     db: Session = Depends(get_db)):
    """Correct a saved set (e.g. a typo). The body is the whole set: empty fields are cleared.
    To record a new value, add a new set instead, so the history keeps the change."""
    m = db.get(BodyMeasurement, measurement_id)
    if m is None or m.user_id != user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Measurement not found")
    values = body.model_dump()
    if all(v is None for v in values.values()):
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "Keep at least one measurement, or delete the set")
    for k, v in values.items():
        setattr(m, k, round(v, 1) if v is not None else None)
    db.commit()
    return body_profile(db, user)


@router.delete("/measurements/{measurement_id}")
def delete_measurement(measurement_id: int, user: User = Depends(onboarded_user), db: Session = Depends(get_db)):
    m = db.get(BodyMeasurement, measurement_id)
    if m is None or m.user_id != user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Measurement not found")
    db.delete(m)
    db.commit()
    return body_profile(db, user)
