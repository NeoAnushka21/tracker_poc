"""The user's food library and recipes (Saved Food tab). Edits here are direct user
actions from the UI, so they apply immediately (the LLM can't reach these routes)."""
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field, field_validator
from sqlalchemy.orm import Session

from app import config
from app.db import get_db
from app.deps import onboarded_user
from app.models import User, UserFood, utcnow
from app.services import labels, micros
from app.services.foods import (
    NUTRIENTS, FoodError, apply_label, compute_recipe, correct_past_logs, find_by_name, food_to_dict, get_user_food,
    list_foods, name_key, normalize_unit, recipes_using, save_recipe, typed_ingredient,
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
    # "These values are from the pack label" (branded foods). Left out = unchanged.
    label_checked: bool | None = None
    # Also recompute past logs of this food with the new numbers.
    correct_logs: bool = False

    @field_validator("micronutrients")
    @classmethod
    def _known_and_non_negative(cls, v: dict | None) -> dict | None:
        for key, value in (v or {}).items():
            if key not in config.MICRONUTRIENT_KEYS:
                raise ValueError(f"Unknown nutrient '{key}'")
            if value is not None and value < 0:
                raise ValueError(f"{key} can't be negative")
        return v


class LabelIn(BaseModel):
    code: str = Field(min_length=8, max_length=14, pattern=r"^\d+$")   # the Open Food Facts barcode
    correct_logs: bool = True


class FoodCreateIn(FoodUpdateIn):
    # Branded product picked on Open Food Facts: its label is fetched again by barcode and
    # replaces the typed numbers.
    label_code: str | None = Field(default=None, min_length=8, max_length=14, pattern=r"^\d+$")


class IngredientIn(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    food_id: int | None = None          # picked from Saved Food
    quantity: float = Field(gt=0)
    unit: str = Field(min_length=1, max_length=32)


class RecipeCreateIn(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    ingredients: list[IngredientIn] = Field(min_length=1, max_length=40)
    yield_pieces: float | None = Field(default=None, gt=0)
    yield_servings: float | None = Field(default=None, gt=0)
    cooked_weight_g: float | None = Field(default=None, gt=0)


def _no_clash(db: Session, user: User, name: str, brand: str | None) -> None:
    if find_by_name(db, user.id, name, brand) is not None:
        what = f"{name} ({brand})" if brand else name
        raise HTTPException(status.HTTP_409_CONFLICT, f"You already have '{what}' in Saved Food. Edit that one instead.")


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


@router.post("", status_code=status.HTTP_201_CREATED)
def create(body: FoodCreateIn, user: User = Depends(onboarded_user), db: Session = Depends(get_db)):
    """+ Add → Generic food or Branded product: a food typed in by the user (or a label they picked)."""
    name, brand = body.name.strip(), (body.brand_name or "").strip() or None
    _no_clash(db, user, name, brand)
    food = UserFood(user_id=user.id, name=name, brand_name=brand, name_key=name_key(name, brand), kind="food",
                    ref_qty=body.ref_qty, ref_unit=normalize_unit(body.ref_unit)[0],
                    **{k: getattr(body, k) for k in NUTRIENTS},
                    grams_per_piece=body.grams_per_piece, grams_per_serving=body.grams_per_serving,
                    micronutrients=micros.clean(body.micronutrients),
                    label_checked=bool(body.label_checked), source="label" if body.label_checked else "user")
    if body.label_code:
        try:
            apply_label(food, labels.get_label(body.label_code))
        except labels.LabelLookupError as e:
            raise HTTPException(status.HTTP_502_BAD_GATEWAY, str(e))
        if body.grams_per_serving:        # the user's own serving weight wins over the label's
            food.grams_per_serving = body.grams_per_serving
    db.add(food)
    db.commit()
    return food_to_dict(food, with_ingredients=True)


def _recipe_payload(db: Session, user: User, body: RecipeCreateIn) -> dict:
    try:
        ingredients = [typed_ingredient(db, user, i.name.strip(), i.quantity, i.unit.strip(), i.food_id)
                       for i in body.ingredients]
        computed = compute_recipe(ingredients, body.yield_pieces, body.yield_servings, body.cooked_weight_g)
    except FoodError as e:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, str(e))
    return {"name": body.name.strip(), "ingredients": ingredients, "yield_pieces": body.yield_pieces,
            "yield_servings": body.yield_servings, "cooked_weight_g": body.cooked_weight_g, **computed}


@router.post("/recipes/preview")
def preview_recipe(body: RecipeCreateIn, user: User = Depends(onboarded_user), db: Session = Depends(get_db)):
    """+ Add → Recipe, Calculate: what the recipe comes to, without saving anything."""
    p = _recipe_payload(db, user, body)
    return {k: p[k] for k in ("ref_qty", "ref_unit", "per_ref", "batch_totals")} | {
        "ingredients": [{"name": i["ingredient_name"], "quantity": i["quantity"], "unit": i["unit"],
                         "calories": i["calories"], "from": i["source"]} for i in p["ingredients"]]}


@router.post("/recipes", status_code=status.HTTP_201_CREATED)
def create_recipe(body: RecipeCreateIn, user: User = Depends(onboarded_user), db: Session = Depends(get_db)):
    """+ Add → Recipe. General-list ingredients are saved to Saved Food too, like a chat recipe."""
    _no_clash(db, user, body.name.strip(), None)
    recipe = save_recipe(db, user, _recipe_payload(db, user, body))
    db.commit()
    db.refresh(recipe)
    return food_to_dict(recipe, with_ingredients=True)


@router.get("/label-search")
def label_search(q: str, _user: User = Depends(onboarded_user)):
    """Pack labels from Open Food Facts for a brand + product name, or a barcode."""
    q = q.strip()[:120]
    if len(q) < 2:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "Type a product name and brand, or a barcode")
    try:
        return labels.search(q)
    except labels.LabelLookupError as e:
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, str(e))


@router.post("/{food_id}/label")
def use_label(food_id: int, body: LabelIn, user: User = Depends(onboarded_user), db: Session = Depends(get_db)):
    """Replace a food's numbers with a pack label the user picked. The label is fetched again
    here by barcode, so only Open Food Facts' own values are saved."""
    food = _food_or_404(db, user, food_id)
    if food.kind == "recipe":
        raise HTTPException(status.HTTP_409_CONFLICT, "A recipe's numbers come from its ingredients")
    try:
        label = labels.get_label(body.code)
    except labels.LabelLookupError as e:
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, str(e))
    if not food.brand_name and label["brand"]:
        clash = find_by_name(db, user.id, food.name, label["brand"])
        if clash is None or clash.id == food.id:
            food.brand_name = label["brand"]
            food.name_key = name_key(food.name, food.brand_name)
    apply_label(food, label)
    corrected = correct_past_logs(db, user, food) if body.correct_logs else 0
    db.commit()
    return {**food_to_dict(food, with_ingredients=True), "logs_corrected": corrected}


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
        if body.label_checked is not None:
            food.label_checked = body.label_checked
            if not body.label_checked:
                food.off_code = None
        # Hand-edited values (and labels) are never overwritten by later estimates.
        food.source = "label" if food.label_checked else "user"
    food.updated_at = utcnow()
    corrected = correct_past_logs(db, user, food) if body.correct_logs and food.kind != "recipe" else 0
    db.commit()
    return {**food_to_dict(food, with_ingredients=True), "logs_corrected": corrected}


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
