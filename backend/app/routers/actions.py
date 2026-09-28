"""The only routes that write food log data. Each needs the user's explicit click."""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import onboarded_user
from app.llm.chat import message_to_dict
from app.models import User
from app.services.actions import action_to_dict, confirm_action, reject_action

router = APIRouter(prefix="/api/actions", tags=["actions"])


@router.post("/{action_id}/confirm")
def confirm(action_id: int, user: User = Depends(onboarded_user), db: Session = Depends(get_db)):
    action, event = confirm_action(db, user, action_id)
    return {"action": action_to_dict(action), "event": message_to_dict(event)}


@router.post("/{action_id}/reject")
def reject(action_id: int, user: User = Depends(onboarded_user), db: Session = Depends(get_db)):
    action, event = reject_action(db, user, action_id)
    return {"action": action_to_dict(action), "event": message_to_dict(event)}
