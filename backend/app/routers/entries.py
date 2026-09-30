"""Dashboard actions on logged food: add, move, copy, change quantity, delete.
These are the user's own clicks on their own entries, so they apply directly. The one
exception is adding a food that isn't saved: its AI estimate becomes a pending action that
the user confirms, the same as in the chat."""
import logging
from datetime import date
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field, field_validator
from sqlalchemy.orm import Session

from app.config import LLM_UNAVAILABLE_MESSAGE, MEAL_TYPES, SHOW_LLM_ERRORS
from app.db import get_db
from app.deps import onboarded_user
from app.llm import usage
from app.llm.estimate import estimate_food
from app.llm.provider import LLMError
from app.models import User
from app.services import allowance
from app.services.actions import action_to_dict
from app.services.entries import (
    add_saved_food, check_target_date, delete_item, owned_item, record_event, set_item_quantity, transfer_items,
)
from app.services.foods import FoodError, closest_saved, get_user_food, library_index, match_saved, measurable_units
from app.services.logs import item_to_dict
from app.timeutil import local_today

log = logging.getLogger("omniai.entries")

router = APIRouter(prefix="/api/entries", tags=["entries"])


class TransferIn(BaseModel):
    to_meal_type: str
    to_date: date | None = None
    mode: Literal["move", "copy"] = "move"

    @field_validator("to_meal_type")
    @classmethod
    def check_meal(cls, v: str) -> str:
        if v not in MEAL_TYPES:
            raise ValueError(f"Meal must be one of {MEAL_TYPES}")
        return v


class QuantityIn(BaseModel):
    quantity: float = Field(gt=0, le=100000)


class AddFoodIn(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    quantity: float = Field(gt=0, le=100000)
    unit: str = Field(min_length=1, max_length=32)
    meal_type: str
    day: date | None = None     # the dashboard's day; None = today
    # Set when the user picked a saved food from the suggestions.
    food_id: int | None = None
    # True after the user said "no" to "Did you mean …?": estimate the name as typed.
    as_typed: bool = False

    @field_validator("name", "unit")
    @classmethod
    def strip(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Can't be blank")
        return v.strip()

    @field_validator("meal_type")
    @classmethod
    def check_meal(cls, v: str) -> str:
        if v not in MEAL_TYPES:
            raise ValueError(f"Meal must be one of {MEAL_TYPES}")
        return v


def _label(meal: str) -> str:
    return meal.replace("_", " ")


@router.post("/items/{item_id}/transfer")
def transfer(item_id: int, body: TransferIn, user: User = Depends(onboarded_user), db: Session = Depends(get_db)):
    item, entry = owned_item(db, user, item_id)
    to_meal = body.to_meal_type
    copy = body.mode == "copy"
    verb = "copied" if copy else "moved"
    what = f"{item.quantity:g} {item.unit} {item.ingredient_name}"
    from_meal = entry.meal_type
    new_entry = transfer_items(db, user, entry, [item], to_meal, body.to_date, copy=copy)
    when = f" on {body.to_date.isoformat()}" if body.to_date else ""
    record_event(db, user, f"On the dashboard the user {verb} {what} from {_label(from_meal)} to {_label(to_meal)}{when} "
                           f"(entry #{new_entry.id}).", new_entry.id)
    db.commit()
    return {"ok": True, "entry_id": new_entry.id}


@router.patch("/items/{item_id}")
def change_quantity(item_id: int, body: QuantityIn, user: User = Depends(onboarded_user), db: Session = Depends(get_db)):
    item, entry = owned_item(db, user, item_id)
    before = f"{item.quantity:g} {item.unit}"
    set_item_quantity(item, body.quantity)
    record_event(db, user, f"On the dashboard the user changed {item.ingredient_name} in entry #{entry.id} "
                           f"from {before} to {item.quantity:g} {item.unit}.", entry.id)
    db.commit()
    return {"ok": True}


@router.delete("/items/{item_id}")
def remove(item_id: int, user: User = Depends(onboarded_user), db: Session = Depends(get_db)):
    item, entry = owned_item(db, user, item_id)
    what = f"{item.quantity:g} {item.unit} {item.ingredient_name}"
    delete_item(entry, item)
    record_event(db, user, f"On the dashboard the user deleted {what} from entry #{entry.id} ({_label(entry.meal_type)}).",
                 entry.id)
    db.commit()
    return {"ok": True}


@router.post("/add")
def add_food(body: AddFoodIn, user: User = Depends(onboarded_user), db: Session = Depends(get_db)):
    """Add a food to a meal. A saved food is added straight away from its saved numbers; any
    other food gets one AI estimate, returned as a pending action to confirm."""
    day = body.day or local_today(user.timezone)
    check_target_date(user, day)
    if body.food_id is not None:
        food = get_user_food(db, user.id, body.food_id)
        if food is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "That saved food no longer exists")
    else:
        food = match_saved(db, user.id, body.name)
        if food is None and not body.as_typed:
            # A typo of a saved food ("panner"): ask instead of guessing, since this adds straight away.
            close = closest_saved(library_index(db, user.id), body.name)
            if close is not None:
                return {"status": "suggest", "food": {"id": close.id, "name": close.name,
                                                       "units": measurable_units(close)}}

    if food is not None:
        try:
            entry = add_saved_food(db, user, food, body.quantity, body.unit, body.meal_type, day)
        except FoodError as e:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT,
                                f"{food.name} is saved per {food.ref_qty:g} {food.ref_unit}, so it can't be "
                                f"added in '{body.unit}'. Use: {', '.join(measurable_units(food))}.") from e
        item = entry.items[0]
        record_event(db, user, f"On the dashboard the user added {item.quantity:g} {item.unit} {item.ingredient_name} "
                               f"from their saved foods to {_label(body.meal_type)} (entry #{entry.id}).", entry.id)
        db.commit()
        return {"status": "added", "entry_id": entry.id, "item": item_to_dict(item)}

    try:
        allowance.check(db, user)   # only new foods use the AI; saved ones above never count
    except allowance.AllowanceExceeded as e:
        raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS, str(e)) from e
    usage.begin()
    try:
        action, note = estimate_food(db, user, body.name, body.quantity, body.unit, body.meal_type, day)
        allowance.record(db, user, "dashboard_add")
        db.commit()
    except LLMError as e:
        db.rollback()
        log.warning("Dashboard estimate failed for user %s: %s", user.id, e)
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, str(e) if SHOW_LLM_ERRORS else LLM_UNAVAILABLE_MESSAGE) from e
    finally:
        try:
            usage.save(db, user.id)
        except Exception:  # never let bookkeeping break the request
            log.exception("Couldn't save LLM usage")
            db.rollback()
    if action is None:
        return {"status": "no_estimate", "message": note}
    return {"status": "estimate", "action": action_to_dict(action), "note": note}
