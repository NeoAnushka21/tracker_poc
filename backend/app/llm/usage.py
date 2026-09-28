"""Collects one record per model call during a chat turn; the chat router saves them after
the turn commits or rolls back, so failed turns are counted too (they still used quota)."""
from contextvars import ContextVar

from sqlalchemy.orm import Session

from app.models import LlmUsage

_records: ContextVar[list[dict] | None] = ContextVar("llm_usage_records", default=None)


def begin() -> None:
    _records.set([])


def record(**fields) -> None:
    """provider, model, tier, intent, prompt_tokens, completion_tokens, latency_ms, outcome, escalated."""
    rows = _records.get()
    if rows is not None:
        rows.append(fields)


def save(db: Session, user_id: int | None) -> None:
    rows = _records.get() or []
    _records.set(None)
    if not rows:
        return
    for r in rows:
        db.add(LlmUsage(user_id=user_id, **r))
    db.commit()
