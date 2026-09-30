"""Human-in-the-loop writes.

The LLM can only *propose* a write (stored as a PendingAction). The write happens in
`confirm_action`, reachable only from the user's Confirm button
(POST /api/actions/{id}/confirm). This is the code-level guarantee that nothing the LLM
suggests is written without explicit user confirmation.
"""
from datetime import date, datetime, timedelta

from fastapi import HTTPException, status
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.config import PENDING_TTL_HOURS
from app.models import ChatMessage, LogEntry, LogEntryItem, PendingAction, User, utcnow
from app.services.foods import FoodError, record_confirmed_items, save_recipe
from app.services.entries import transfer_items
from app.services.logs import get_active_entry
from app.services.water import add_water
from app.timeutil import resolve_meal_type, utc_to_local


def expire_stale(db: Session, user_id: int) -> None:
    cutoff = utcnow() - timedelta(hours=PENDING_TTL_HOURS)
    db.execute(
        update(PendingAction)
        .where(
            PendingAction.user_id == user_id,
            PendingAction.status == "pending",
            PendingAction.created_at < cutoff,
        )
        .values(status="expired", resolved_at=utcnow())
    )


def from_dashboard(a: PendingAction) -> bool:
    """An AI estimate made by the dashboard's Add food. It lives in the dashboard, not the chat:
    the chat neither shows it, sends it to the model, nor replaces it."""
    return (a.payload or {}).get("origin") == "dashboard"


def supersede_older(db: Session, user_id: int, before_id: int) -> None:
    """A new chat proposal replaces any still-open chat proposals from earlier turns."""
    for a in _pending(db, user_id):
        if a.id < before_id and not from_dashboard(a):
            a.status, a.resolved_at = "superseded", utcnow()


def _pending(db: Session, user_id: int) -> list[PendingAction]:
    stmt = select(PendingAction).where(
        PendingAction.user_id == user_id, PendingAction.status == "pending"
    ).order_by(PendingAction.id)
    return list(db.scalars(stmt))


def open_actions(db: Session, user_id: int) -> list[PendingAction]:
    """Open chat proposals (dashboard estimates excluded)."""
    return [a for a in _pending(db, user_id) if not from_dashboard(a)]


def action_to_dict(a: PendingAction) -> dict:
    return {
        "id": a.id,
        "action_type": a.action_type,
        "status": a.status,
        "target_entry_id": a.target_entry_id,
        "result_entry_id": a.result_entry_id,
        "payload": a.payload,
    }


def _get_open_action(db: Session, user: User, action_id: int) -> PendingAction:
    expire_stale(db, user.id)
    action = db.get(PendingAction, action_id)
    if action is None or action.user_id != user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Proposal not found")
    if action.status != "pending":
        raise HTTPException(status.HTTP_409_CONFLICT, f"This proposal is already {action.status}")
    return action


def _log_event(db: Session, user_id: int, text: str, entry_id: int | None = None) -> ChatMessage:
    msg = ChatMessage(user_id=user_id, role="event", content=text, related_log_entry_id=entry_id)
    db.add(msg)
    return msg


def _meal_type(payload: dict, user: User) -> str:
    """Proposals made before morning/evening snacks existed may still say 'snack'."""
    local = utc_to_local(datetime.fromisoformat(payload["eaten_at_utc"]), user.timezone)
    return resolve_meal_type(payload["meal_type"], local)


def _items_from_payload(payload: dict) -> list[LogEntryItem]:
    return [
        LogEntryItem(
            ingredient_name=i["ingredient_name"],
            brand_name=i.get("brand_name"),
            quantity=i["quantity"],
            unit=i["unit"],
            calories=i["calories"],
            protein_g=i["protein_g"],
            carbs_g=i["carbs_g"],
            fat_g=i["fat_g"],
            fiber_g=i.get("fiber_g", 0),
            micronutrients=i.get("micronutrients"),
            user_food_id=i.get("food_id"),
            general_id=i.get("general_id"),
            source=i.get("source"),
        )
        for i in payload["items"]
    ]


def _link_learned(items: list[LogEntryItem], foods: list) -> None:
    """Point each logged item at the saved food it was logged from or just learned into."""
    for item, food in zip(items, foods):
        if food is not None:
            item.user_food_id = food.id


def confirm_action(db: Session, user: User, action_id: int) -> tuple[PendingAction, ChatMessage]:
    action = _get_open_action(db, user, action_id)
    p = action.payload

    if action.action_type == "water":
        log = add_water(db, user, p["amount_ml"], datetime.fromisoformat(p["drank_at_utc"]))
        action.status, action.resolved_at = "confirmed", utcnow()
        event = _log_event(db, user.id, f"User confirmed proposal #{action.id}; {log.amount_ml:g} ml water logged.")
        db.commit()
        return action, event

    if action.action_type == "save_recipe":
        try:
            recipe = save_recipe(db, user, p)
        except FoodError as e:
            db.rollback()
            raise HTTPException(status.HTTP_409_CONFLICT, str(e)) from e
        action.status, action.resolved_at = "confirmed", utcnow()
        event = _log_event(
            db, user.id,
            f"User confirmed proposal #{action.id}; recipe '{recipe.name}' saved to their library as food #{recipe.id}.",
        )
        db.commit()
        return action, event

    if action.action_type == "create":
        entry = LogEntry(
            user_id=user.id,
            eaten_at=datetime.fromisoformat(p["eaten_at_utc"]),
            meal_type=_meal_type(p, user),
            raw_user_message=p.get("raw_user_message"),
            items=_items_from_payload(p),
        )
        db.add(entry)
        db.flush()
        _link_learned(entry.items, record_confirmed_items(db, user, p["items"]))
        if from_dashboard(action):
            what = ", ".join(f"{i['quantity']:g} {i['unit']} {i['ingredient_name']}" for i in p["items"])
            event_text = (f"On the dashboard the user added {what} to {entry.meal_type.replace('_', ' ')} "
                          f"(AI estimate, confirmed; entry #{entry.id}).")
        else:
            event_text = f"User confirmed proposal #{action.id}; saved as log entry #{entry.id}."

    else:
        entry = get_active_entry(db, user.id, action.target_entry_id)
        if entry is None:
            action.status, action.resolved_at = "expired", utcnow()
            db.commit()
            raise HTTPException(status.HTTP_409_CONFLICT, "That entry no longer exists")

        if action.action_type == "edit":
            entry.items = _items_from_payload(p)
            entry.meal_type = _meal_type(p, user)
            entry.eaten_at = datetime.fromisoformat(p["eaten_at_utc"])
            entry.updated_at = utcnow()
            db.flush()
            _link_learned(entry.items, record_confirmed_items(db, user, p["items"]))
            event_text = f"User confirmed proposal #{action.id}; log entry #{entry.id} updated."
        elif action.action_type == "delete":
            entry.deleted_at = utcnow()
            event_text = f"User confirmed proposal #{action.id}; log entry #{entry.id} deleted."
        elif action.action_type in ("move", "copy"):
            by_id = {i.id: i for i in entry.items}
            if not all(i in by_id for i in p["item_ids"]):
                action.status, action.resolved_at = "expired", utcnow()
                db.commit()
                raise HTTPException(status.HTTP_409_CONFLICT, "Those foods changed since this was proposed")
            to_date = date.fromisoformat(p["to_date"]) if p.get("to_date") else None
            result = transfer_items(db, user, entry, [by_id[i] for i in p["item_ids"]],
                                    p["to_meal_type"], to_date, copy=action.action_type == "copy")
            verb = "copied" if action.action_type == "copy" else "moved"
            event_text = (f"User confirmed proposal #{action.id}; food {verb} from entry #{entry.id} "
                          f"to {p['to_meal_type']} (entry #{result.id}).")
            entry = result
        else:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Unknown action type")

    action.status = "confirmed"
    action.resolved_at = utcnow()
    action.result_entry_id = entry.id
    event = _log_event(db, user.id, event_text, entry.id)
    db.commit()
    return action, event


def reject_action(db: Session, user: User, action_id: int) -> tuple[PendingAction, ChatMessage]:
    action = _get_open_action(db, user, action_id)
    action.status = "rejected"
    action.resolved_at = utcnow()
    text = ("On the dashboard the user discarded an AI estimate; nothing was saved." if from_dashboard(action)
            else f"User cancelled proposal #{action.id}; nothing was saved.")
    event = _log_event(db, user.id, text)
    db.commit()
    return action, event
