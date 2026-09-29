"""Item-level changes to confirmed log entries: add, move, copy, change quantity, delete.

Shared by the chat (after the user confirms a proposal) and the dashboard (direct clicks).
Move/copy happen in one step, so nothing is ever deleted before its copy exists.
"""
from datetime import date, datetime, time

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.config import MEAL_DEFAULT_TIMES
from app.models import ChatMessage, LogEntry, LogEntryItem, User, UserFood, utcnow
from app.services import micros
from app.services.foods import nutrients_for
from app.services.logs import NUTRIENTS, entries_between, get_active_entry
from app.timeutil import local_to_utc, local_today, utc_to_local


def owned_item(db: Session, user: User, item_id: int) -> tuple[LogEntryItem, LogEntry]:
    item = db.get(LogEntryItem, item_id)
    entry = get_active_entry(db, user.id, item.log_entry_id) if item else None
    if item is None or entry is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "That food isn't in your logs any more")
    return item, entry


def _clone(item: LogEntryItem) -> LogEntryItem:
    return LogEntryItem(
        ingredient_name=item.ingredient_name, brand_name=item.brand_name, quantity=item.quantity,
        unit=item.unit, micronutrients=dict(item.micronutrients) if item.micronutrients else None,
        **{k: getattr(item, k) for k in NUTRIENTS},
    )


def _eaten_at_on(entry: LogEntry, user: User, to_date: date | None) -> datetime:
    """Same local time of day as the source entry, on the target date."""
    if to_date is None:
        return entry.eaten_at
    local = utc_to_local(entry.eaten_at, user.timezone)
    return local_to_utc(datetime.combine(to_date, local.time().replace(tzinfo=None)), user.timezone)


def check_target_date(user: User, to_date: date | None) -> None:
    if to_date is not None and to_date > local_today(user.timezone):
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "Can't log food on a future date")


def transfer_items(db: Session, user: User, entry: LogEntry, items: list[LogEntryItem],
                   to_meal: str, to_date: date | None, copy: bool) -> LogEntry:
    """Move (or copy) some or all of an entry's items to another meal and/or date."""
    check_target_date(user, to_date)
    whole_entry = {i.id for i in items} == {i.id for i in entry.items}
    if not copy and whole_entry:
        entry.meal_type = to_meal
        entry.eaten_at = _eaten_at_on(entry, user, to_date)
        entry.updated_at = utcnow()
        db.flush()
        return entry

    new_entry = LogEntry(
        user_id=user.id, meal_type=to_meal, eaten_at=_eaten_at_on(entry, user, to_date),
        raw_user_message=entry.raw_user_message, items=[_clone(i) for i in items],
    )
    db.add(new_entry)
    if not copy:
        for i in items:
            entry.items.remove(i)          # delete-orphan removes the row
        _soft_delete_if_empty(entry)
    db.flush()
    return new_entry


def eaten_at_for_meal(db: Session, user: User, meal: str, day: date) -> datetime:
    """Time for food added to a meal from the dashboard: the meal's latest entry that day, else
    the meal's usual time, but never later than now (so today's dinner added at 3 pm is 3 pm)."""
    same_meal = [e.eaten_at for e in entries_between(db, user, day, day) if e.meal_type == meal]
    if same_meal:
        return max(same_meal)
    usual = local_to_utc(datetime.combine(day, time(*MEAL_DEFAULT_TIMES[meal])), user.timezone)
    return min(usual, utcnow())


def add_saved_food(db: Session, user: User, food: UserFood, quantity: float, unit: str,
                   meal: str, day: date) -> LogEntry:
    """Dashboard add of a saved food: its stored numbers, scaled in code (no model involved).
    Raises FoodError if the unit can't be converted for this food."""
    check_target_date(user, day)
    nutrients = nutrients_for(food, quantity, unit)
    entry = LogEntry(
        user_id=user.id, meal_type=meal, eaten_at=eaten_at_for_meal(db, user, meal, day),
        items=[LogEntryItem(ingredient_name=food.name, brand_name=food.brand_name, quantity=quantity,
                            unit=unit, **nutrients)],
    )
    db.add(entry)
    food.last_used_at = utcnow()
    db.flush()
    return entry


def set_item_quantity(item: LogEntryItem, quantity: float) -> None:
    """Change the amount; nutrients (and micronutrients) scale proportionally."""
    if quantity <= 0:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "Quantity must be more than 0")
    factor = quantity / item.quantity
    for k in NUTRIENTS:
        setattr(item, k, round((getattr(item, k) or 0) * factor, 1))
    item.micronutrients = micros.scale(item.micronutrients, factor)
    item.quantity = quantity


def delete_item(entry: LogEntry, item: LogEntryItem) -> None:
    entry.items.remove(item)
    _soft_delete_if_empty(entry)


def _soft_delete_if_empty(entry: LogEntry) -> None:
    if not entry.items:
        entry.deleted_at = utcnow()


def record_event(db: Session, user: User, text: str, entry_id: int | None = None) -> None:
    """Tell MacBro (via chat history) about changes made outside the chat."""
    db.add(ChatMessage(user_id=user.id, role="event", content=text, related_log_entry_id=entry_id))
