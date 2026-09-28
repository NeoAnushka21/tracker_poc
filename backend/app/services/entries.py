"""Item-level changes to confirmed log entries: move, copy, change quantity, delete.

Shared by the chat (after the user confirms a proposal) and the dashboard (direct clicks).
Move/copy happen in one step, so nothing is ever deleted before its copy exists.
"""
from datetime import date, datetime

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models import ChatMessage, LogEntry, LogEntryItem, User, utcnow
from app.services import micros
from app.services.logs import NUTRIENTS, get_active_entry
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
