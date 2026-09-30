"""Download my data: everything stored about a user, as one JSON document (right of access,
India's DPDP Act 2023). Secrets are left out: the password hash and the Google account id."""
import uuid
from datetime import date, datetime

from sqlalchemy import inspect, select
from sqlalchemy.orm import Session

from app.config import APP_NAME
from app.models import (
    AdminAudit, AiRequest, BodyMeasurement, ChatMessage, LlmUsage, LogEntry, PendingAction, User, UserFood,
    UserTarget, WaterLog, WeightLog, utcnow,
)

_SECRET = {"hashed_password", "google_sub"}


def _value(v):
    if isinstance(v, datetime):
        return v.isoformat() + "Z"          # stored as naive UTC
    if isinstance(v, date):
        return v.isoformat()
    if isinstance(v, uuid.UUID):
        return str(v)
    return v


def _row(obj, skip: set[str] = frozenset()) -> dict:
    return {c.key: _value(getattr(obj, c.key)) for c in inspect(obj).mapper.column_attrs
            if c.key not in _SECRET and c.key not in skip}


def _all(db: Session, model, uid: int, order) -> list:
    return list(db.scalars(select(model).where(model.user_id == uid).order_by(order)))


def export_user_data(db: Session, user: User) -> dict:
    uid = user.id
    entries = _all(db, LogEntry, uid, LogEntry.eaten_at)
    foods = _all(db, UserFood, uid, UserFood.id)
    views = db.scalars(select(AdminAudit).where(AdminAudit.target_user_id == uid).order_by(AdminAudit.id))
    return {
        "about": f"All data {APP_NAME} stores about your account, exported {utcnow().isoformat()}Z. "
                 "Times ending in Z are UTC.",
        "account": {**_row(user), "has_password": bool(user.hashed_password),
                    "google_linked": user.google_sub is not None},
        "weight_logs": [_row(w, {"user_id"}) for w in _all(db, WeightLog, uid, WeightLog.logged_at)],
        "targets": [_row(t, {"user_id"}) for t in _all(db, UserTarget, uid, UserTarget.id)],
        "body_measurements": [_row(m, {"user_id"}) for m in _all(db, BodyMeasurement, uid, BodyMeasurement.measured_at)],
        "food_log": [{**_row(e, {"user_id"}), "items": [_row(i, {"log_entry_id"}) for i in e.items]} for e in entries],
        "water_logs": [_row(w, {"user_id"}) for w in _all(db, WaterLog, uid, WaterLog.drank_at)],
        "my_foods": [{**_row(f, {"user_id"}),
                      "ingredients": [_row(ri, {"recipe_id"}) for ri in f.ingredients]} for f in foods],
        "chat_messages": [_row(m, {"user_id"}) for m in _all(db, ChatMessage, uid, ChatMessage.id)],
        "proposals": [_row(a, {"user_id"}) for a in _all(db, PendingAction, uid, PendingAction.id)],
        "ai_requests": [_row(r, {"user_id"}) for r in _all(db, AiRequest, uid, AiRequest.id)],
        "ai_model_calls": [_row(u, {"user_id"}) for u in _all(db, LlmUsage, uid, LlmUsage.id)],
        "about_you": _row(user.preferences, {"user_id"}) if user.preferences else None,
        "admin_views_of_your_data": [{"at": _value(v.created_at), "action": v.action} for v in views],
    }
