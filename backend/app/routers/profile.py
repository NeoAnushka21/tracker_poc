from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db import get_db
from app.config import CONSENT_VERSION
from app.deps import current_user, is_admin, onboarded_user
from app.models import User, UserTarget, WeightLog
from app.nutrition import age_on, calculate_targets
from app.schemas import OnboardingIn, TargetsIn, WeightIn
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
