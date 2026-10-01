import logging
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.config import LLM_UNAVAILABLE_MESSAGE, SHOW_LLM_ERRORS
from app.db import get_db
from app.deps import onboarded_user
from app.llm import usage
from app.llm.chat import handle_user_message, message_to_dict, messages_for_day, recent_messages
from app.llm.provider import LLMError
from app.models import User
from app.schemas import CancelIn, ChatIn
from app.services import allowance, cancel
from app.services.actions import expire_stale
from app.timeutil import local_today

router = APIRouter(prefix="/api/chat", tags=["chat"])
log = logging.getLogger("macbro.chat")


@router.get("/history")
def history(limit: int = 100, user: User = Depends(onboarded_user), db: Session = Depends(get_db)):
    expire_stale(db, user.id)
    db.commit()
    return [message_to_dict(m) for m in recent_messages(db, user.id, min(limit, 500))]


@router.get("/day")
def chat_day(day: date | None = None, user: User = Depends(onboarded_user), db: Session = Depends(get_db)):
    """One local day of chat (default today: a fresh chat each day) and the previous day with messages."""
    expire_stale(db, user.id)
    db.commit()
    day = day or local_today(user.timezone)
    msgs, prev_day = messages_for_day(db, user, day)
    return {"day": day.isoformat(), "messages": [message_to_dict(m) for m in msgs],
            "prev_day": prev_day.isoformat() if prev_day else None}


@router.post("")
def send(body: ChatIn, user: User = Depends(onboarded_user), db: Session = Depends(get_db)):
    usage.begin()
    try:
        return handle_user_message(db, user, body.message.strip(), body.feedback_on_action_id,
                                   body.client_request_id, body.log_date, body.barcode)
    except cancel.ChatCancelled:
        db.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, "cancelled")
    except allowance.AllowanceExceeded as e:
        db.rollback()   # the message isn't kept; the browser puts it back in the input box
        raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS, str(e)) from e
    except LLMError as e:
        db.rollback()
        log.warning("LLM call failed for user %s: %s", user.id, e)
        detail = str(e) if SHOW_LLM_ERRORS else LLM_UNAVAILABLE_MESSAGE
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, detail) from e
    finally:
        # Saved after the turn commits or rolls back: failed calls used quota too.
        try:
            usage.save(db, user.id)
        except Exception:  # never let bookkeeping break the chat
            log.exception("Couldn't save LLM usage")
            db.rollback()


@router.get("/allowance")
def ai_allowance(user: User = Depends(onboarded_user), db: Session = Depends(get_db)):
    """Today's AI allowance: {limit, used, remaining, resets_at} (limit null = unlimited)."""
    return allowance.status(db, user)


@router.post("/cancel")
def cancel_turn(body: CancelIn, user: User = Depends(onboarded_user)):
    """Stop button. 'finished' means the reply was already saved; the UI then reloads it."""
    return {"status": cancel.cancel(user.id, body.client_request_id)}
