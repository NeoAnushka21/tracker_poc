import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.config import LLM_UNAVAILABLE_MESSAGE, SHOW_LLM_ERRORS
from app.db import get_db
from app.deps import onboarded_user
from app.llm.chat import handle_user_message, message_to_dict, recent_messages
from app.llm.provider import LLMError
from app.models import User
from app.schemas import CancelIn, ChatIn
from app.services import cancel
from app.services.actions import expire_stale

router = APIRouter(prefix="/api/chat", tags=["chat"])
log = logging.getLogger("macbro.chat")


@router.get("/history")
def history(limit: int = 100, user: User = Depends(onboarded_user), db: Session = Depends(get_db)):
    expire_stale(db, user.id)
    db.commit()
    return [message_to_dict(m) for m in recent_messages(db, user.id, min(limit, 500))]


@router.post("")
def send(body: ChatIn, user: User = Depends(onboarded_user), db: Session = Depends(get_db)):
    try:
        return handle_user_message(db, user, body.message.strip(), body.feedback_on_action_id,
                                   body.client_request_id)
    except cancel.ChatCancelled:
        db.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, "cancelled")
    except LLMError as e:
        db.rollback()
        log.warning("LLM call failed for user %s: %s", user.id, e)
        detail = str(e) if SHOW_LLM_ERRORS else LLM_UNAVAILABLE_MESSAGE
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, detail) from e


@router.post("/cancel")
def cancel_turn(body: CancelIn, user: User = Depends(onboarded_user)):
    """Stop button. 'finished' means the reply was already saved; the UI then reloads it."""
    return {"status": cancel.cancel(user.id, body.client_request_id)}
