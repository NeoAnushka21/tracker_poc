"""Apply or reject the chat assistant's proposals. The LLM can only propose; these routes run on the
user's Confirm/Cancel click. (Dashboard edits in routers/entries.py are direct user clicks.)"""
from datetime import date, datetime

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import onboarded_user
from app.llm.chat import message_to_dict
from app.models import ChatMessage, User
from app.services.actions import action_to_dict, choose_label, confirm_action, from_dashboard, reject_action
from app.services.progress import build_progress, build_water_progress
from app.timeutil import utc_to_local

# Confirmed actions that change the day's totals get a "day so far" card in the chat:
# water logs a water card, food changes the calories-and-macros card.
PROGRESS_AFTER = {"create", "edit", "delete", "move", "copy", "water"}


def _action_day(payload: dict, user: User) -> date | None:
    """The local day the confirmed change landed on (None = today)."""
    for key in ("drank_at_utc", "eaten_at_utc"):
        if payload.get(key):
            return utc_to_local(datetime.fromisoformat(payload[key]), user.timezone).date()
    return date.fromisoformat(payload["to_date"]) if payload.get("to_date") else None

router = APIRouter(prefix="/api/actions", tags=["actions"])


@router.post("/{action_id}/confirm")
def confirm(action_id: int, user: User = Depends(onboarded_user), db: Session = Depends(get_db)):
    action, event = confirm_action(db, user, action_id)
    progress = None
    # Dashboard adds show their result on the dashboard, so no card is posted into the chat.
    if action.action_type in PROGRESS_AFTER and not from_dashboard(action):
        day = _action_day(action.payload, user)
        text, data = (build_water_progress if action.action_type == "water" else build_progress)(db, user, day)
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


class LabelChoiceIn(BaseModel):
    # A product's barcode from the card's choices; null = "none of these" (keep the AI's estimate).
    code: str | None = Field(default=None, pattern=r"^\d{8,14}$")


@router.post("/{action_id}/items/{index}/label")
def pick_label(action_id: int, index: int, body: LabelChoiceIn, user: User = Depends(onboarded_user),
               db: Session = Depends(get_db)):
    """A branded item's pack label, picked on the card (before Looks good)."""
    return action_to_dict(choose_label(db, user, action_id, index, body.code))


@router.post("/{action_id}/items/{index}/label-search")
def search_label_again(action_id: int, index: int, user: User = Depends(onboarded_user), db: Session = Depends(get_db)):
    """"Find the label" when Open Food Facts didn't answer in time."""
    return action_to_dict(choose_label(db, user, action_id, index, None, search_again=True))
