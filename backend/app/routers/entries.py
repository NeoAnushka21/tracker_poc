"""Dashboard actions on a single logged food: move, copy, change quantity, delete.
These are the user's own clicks on their own entries, so they apply directly."""
from datetime import date
from typing import Literal

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field, field_validator
from sqlalchemy.orm import Session

from app.config import MEAL_TYPES
from app.db import get_db
from app.deps import onboarded_user
from app.models import User
from app.services.entries import delete_item, owned_item, record_event, set_item_quantity, transfer_items

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
