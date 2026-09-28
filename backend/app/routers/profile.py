from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.config import CONSENT_VERSION
from app.deps import current_user, is_admin, onboarded_user
from app.config import BODY_PARTS, BODY_PART_KEYS
from app.models import BodyMeasurement, User, UserTarget, WeightLog
from app.nutrition import age_on, calculate_targets
from app.schemas import HeightIn, MeasurementsIn, OnboardingIn, TargetsIn, WeightIn
from app.services.body import SAME_SESSION_DAYS, bmi, body_fat_navy
from app.services.logs import current_targets, current_weight, targets_to_dict
from app.timeutil import is_valid_timezone, local_today

router = APIRouter(prefix="/api/profile", tags=["profile"])


def user_to_dict(db: Session, user: User) -> dict:
    weight = current_weight(db, user.id)
    return {
        "id": user.id,
        "email": user.email,
        "onboarded": user.onboarded,
        "preferred_name": user.preferred_name,
        "date_of_birth": user.date_of_birth.isoformat() if user.date_of_birth else None,
        "sex": user.sex,
        "height_cm": user.height_cm,
        "weight_kg": weight.weight_kg if weight else None,
        "unit_system": user.unit_system,
        "timezone": user.timezone,
        "goal_type": user.goal_type,
        "activity_level": user.activity_level,
        "targets": targets_to_dict(current_targets(db, user.id)),
        "consented": user.consent_version == CONSENT_VERSION,
        "is_admin": is_admin(user),
        "created_at": user.created_at.isoformat() + "Z" if user.created_at else None,
        "last_login_at": user.last_login_at.isoformat() + "Z" if user.last_login_at else None,
        "consented_at": user.consent_at.isoformat() + "Z" if user.consent_at else None,
        "guide_seen": user.guide_seen_at is not None,
    }


def _calculated_targets(user: User, weight_kg: float):
    return calculate_targets(
        weight_kg=weight_kg,
        height_cm=user.height_cm,
        age=age_on(user.date_of_birth, local_today(user.timezone)),
        sex=user.sex,
        activity_level=user.activity_level,
        goal_type=user.goal_type,
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


@router.post("/onboarding")
def onboarding(body: OnboardingIn, user: User = Depends(current_user), db: Session = Depends(get_db)):
    if not is_valid_timezone(body.timezone):
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, f"Unknown time zone '{body.timezone}'")
    for field in ("preferred_name", "date_of_birth", "sex", "height_cm", "unit_system",
                  "timezone", "goal_type", "activity_level"):
        setattr(user, field, getattr(body, field))
    if user.preferred_name is not None:
        user.preferred_name = user.preferred_name.strip() or None

    db.add(WeightLog(user_id=user.id, weight_kg=body.weight_kg))
    calc = _save_calculated_targets(db, user, body.weight_kg)
    db.commit()
    return {**user_to_dict(db, user), "calculation": calc}


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
