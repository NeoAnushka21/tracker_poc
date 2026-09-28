"""Apply or reject MacBro's proposals. The LLM can only propose; these routes run on the
user's Confirm/Cancel click. (Dashboard edits in routers/entries.py are direct user clicks.)"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import onboarded_user
from app.llm.chat import message_to_dict
from app.models import ChatMessage, User
from app.services.actions import action_to_dict, confirm_action, reject_action
from app.services.progress import build_progress

# Confirmed actions that change the day's totals get a "day so far" card in the chat.
PROGRESS_AFTER = {"create", "edit", "delete", "move", "copy", "water"}

router = APIRouter(prefix="/api/actions", tags=["actions"])


@router.post("/{action_id}/confirm")
def confirm(action_id: int, user: User = Depends(onboarded_user), db: Session = Depends(get_db)):
    action, event = confirm_action(db, user, action_id)
    progress = None
    if action.action_type in PROGRESS_AFTER:
        text, data = build_progress(db, user)
        progress = ChatMessage(user_id=user.id, role="assistant", kind="progress", content=text, data=data)
        db.add(progress)
        db.commit()
    return {
        "action": action_to_dict(action),
        "event": message_to_dict(event),
        "progress": message_to_dict(progress) if progress else None,
    }


@router.post("/{action_id}/reject")
def reject(action_id: int, user: User = Depends(onboarded_user), db: Session = Depends(get_db)):
    action, event = reject_action(db, user, action_id)
    return {"action": action_to_dict(action), "event": message_to_dict(event)}
