"""The user's food library and recipes (Saved Food tab). Edits here are direct user
actions from the UI, so they apply immediately (the LLM can't reach these routes)."""
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field, field_validator
from sqlalchemy.orm import Session

from app import config
from app.db import get_db
from app.deps import onboarded_user
from app.models import User, utcnow
from app.services import micros
from app.services.foods import (
    NUTRIENTS, find_by_name, food_to_dict, get_user_food, list_foods, name_key, normalize_unit, recipes_using,
)

router = APIRouter(prefix="/api/foods", tags=["foods"])


class FoodUpdateIn(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    brand_name: str | None = Field(default=None, max_length=200)
    # Nutrition fields are ignored for recipes (their numbers come from the ingredients).
    ref_qty: float = Field(gt=0)
    ref_unit: str = Field(min_length=1, max_length=32)
    calories: float = Field(ge=0)
    protein_g: float = Field(ge=0)
    carbs_g: float = Field(ge=0)
    fat_g: float = Field(ge=0)
    fiber_g: float = Field(default=0, ge=0)
    grams_per_piece: float | None = Field(default=None, gt=0)
    grams_per_serving: float | None = Field(default=None, gt=0)
    # Per the same reference amount as the macros ({"iron_mg": 0.4, ...}). A missing key means
    # "unknown", not zero. Leaving the field out of the request keeps the stored values.
    micronutrients: dict[str, float | None] | None = None

    @field_validator("micronutrients")
    @classmethod
    def _known_and_non_negative(cls, v: dict | None) -> dict | None:
        for key, value in (v or {}).items():
            if key not in config.MICRONUTRIENT_KEYS:
                raise ValueError(f"Unknown nutrient '{key}'")
            if value is not None and value < 0:
                raise ValueError(f"{key} can't be negative")
        return v


def _food_or_404(db: Session, user: User, food_id: int):
    food = get_user_food(db, user.id, food_id)
    if food is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Food not found")
    return food


@router.get("")
def list_all(user: User = Depends(onboarded_user), db: Session = Depends(get_db)):
    return [food_to_dict(f, with_ingredients=True) for f in list_foods(db, user.id)]


@router.get("/micronutrients")
def micronutrient_fields(_user: User = Depends(onboarded_user)):
    """The micronutrients a food can carry (labels and units for the edit form)."""
    return [{"key": key, "label": label, "unit": unit, "kind": kind}
            for key, label, unit, kind, _ in config.MICRONUTRIENTS]


@router.get("/{food_id}")
def get_one(food_id: int, user: User = Depends(onboarded_user), db: Session = Depends(get_db)):
    return food_to_dict(_food_or_404(db, user, food_id), with_ingredients=True)


@router.put("/{food_id}")
def update(food_id: int, body: FoodUpdateIn, user: User = Depends(onboarded_user), db: Session = Depends(get_db)):
    food = _food_or_404(db, user, food_id)
    brand = None if food.kind == "recipe" else (body.brand_name or None)
    clash = find_by_name(db, user.id, body.name, brand)
    if clash is not None and clash.id != food.id:
        raise HTTPException(status.HTTP_409_CONFLICT, f"You already have a food called '{body.name}'")
    food.name = body.name.strip()
    food.brand_name = brand
    food.name_key = name_key(food.name, brand)
    if food.kind != "recipe":
        food.ref_qty = body.ref_qty
        food.ref_unit, _ = normalize_unit(body.ref_unit)
        for k in NUTRIENTS:
            setattr(food, k, getattr(body, k))
        food.grams_per_piece = body.grams_per_piece
        food.grams_per_serving = body.grams_per_serving
        if "micronutrients" in body.model_fields_set:
            food.micronutrients = micros.clean(body.micronutrients)
        food.source = "user"   # hand-edited values are never overwritten by later estimates
    food.updated_at = utcnow()
    db.commit()
    return food_to_dict(food, with_ingredients=True)


@router.delete("/{food_id}")
def delete(food_id: int, user: User = Depends(onboarded_user), db: Session = Depends(get_db)):
    food = _food_or_404(db, user, food_id)
    used_in = [r.name for r in recipes_using(db, food.id)]
    if used_in:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            f"'{food.name}' is an ingredient in: {', '.join(used_in)}. Delete or change those recipes first.",
        )
    db.delete(food)
    db.commit()
    return {"ok": True}
