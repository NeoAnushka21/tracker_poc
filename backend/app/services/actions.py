"""Human-in-the-loop writes.

The LLM can only *propose* a create/edit/delete (stored as a PendingAction).
The actual database write happens in `confirm_action`, which is only reachable
from the user's Confirm button (POST /api/actions/{id}/confirm). This is the
code-level guarantee that nothing is written without explicit user confirmation.
"""
from datetime import datetime, timedelta

from fastapi import HTTPException, status
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.config import PENDING_TTL_HOURS
from app.models import ChatMessage, LogEntry, LogEntryItem, PendingAction, User, utcnow
from app.services.logs import get_active_entry


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


def supersede_older(db: Session, user_id: int, before_id: int) -> None:
    """A new proposal replaces any still-open proposals from earlier turns."""
    db.execute(
        update(PendingAction)
        .where(
            PendingAction.user_id == user_id,
            PendingAction.status == "pending",
            PendingAction.id < before_id,
        )
        .values(status="superseded", resolved_at=utcnow())
    )


def open_actions(db: Session, user_id: int) -> list[PendingAction]:
    stmt = select(PendingAction).where(
        PendingAction.user_id == user_id, PendingAction.status == "pending"
    ).order_by(PendingAction.id)
    return list(db.scalars(stmt))


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
        )
        for i in payload["items"]
    ]


def confirm_action(db: Session, user: User, action_id: int) -> tuple[PendingAction, ChatMessage]:
    action = _get_open_action(db, user, action_id)
    p = action.payload

    if action.action_type == "create":
        entry = LogEntry(
            user_id=user.id,
            eaten_at=datetime.fromisoformat(p["eaten_at_utc"]),
            meal_type=p["meal_type"],
            raw_user_message=p.get("raw_user_message"),
            items=_items_from_payload(p),
        )
        db.add(entry)
        db.flush()
        event_text = f"User confirmed proposal #{action.id}; saved as log entry #{entry.id}."

    else:
        entry = get_active_entry(db, user.id, action.target_entry_id)
        if entry is None:
            action.status, action.resolved_at = "expired", utcnow()
            db.commit()
            raise HTTPException(status.HTTP_409_CONFLICT, "That entry no longer exists")

        if action.action_type == "edit":
            entry.items = _items_from_payload(p)
            entry.meal_type = p["meal_type"]
            entry.eaten_at = datetime.fromisoformat(p["eaten_at_utc"])
            entry.updated_at = utcnow()
            event_text = f"User confirmed proposal #{action.id}; log entry #{entry.id} updated."
        elif action.action_type == "delete":
            entry.deleted_at = utcnow()
            event_text = f"User confirmed proposal #{action.id}; log entry #{entry.id} deleted."
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
    event = _log_event(db, user.id, f"User cancelled proposal #{action.id}; nothing was saved.")
    db.commit()
    return action, event
