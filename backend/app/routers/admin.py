"""Admin panel API: read-only access to users and the data they've shared.

Access is limited to ADMIN_EMAILS, and every view of a user's data is written to
admin_audit so there's a record of who looked at what.
"""
from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import admin_user, is_admin
from app.llm.chat import message_to_dict, recent_messages
from app.models import AdminAudit, ChatMessage, LogEntry, User, UserFood, WaterLog, WeightLog
from app.routers.profile import body_profile, user_to_dict
from app.services.foods import food_to_dict, list_foods
from app.services.logs import logs_by_day
from app.timeutil import local_today

router = APIRouter(prefix="/api/admin", tags=["admin"])


def _iso(dt) -> str | None:
    return dt.isoformat() + "Z" if dt else None


def _audit(db: Session, admin: User, target_id: int | None, action: str) -> None:
    db.add(AdminAudit(admin_user_id=admin.id, target_user_id=target_id, action=action))
    db.commit()


def _target(db: Session, user_id: int) -> User:
    user = db.get(User, user_id)
    if user is None or is_admin(user):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "User not found")
    return user


def _counts(db: Session, model, user_ids: list[int], extra=None) -> dict[int, int]:
    stmt = select(model.user_id, func.count()).where(model.user_id.in_(user_ids)).group_by(model.user_id)
    if extra is not None:
        stmt = stmt.where(extra)
    return dict(db.execute(stmt).all())


@router.get("/users")
def list_users(admin: User = Depends(admin_user), db: Session = Depends(get_db)):
    # Only app users: admin accounts aren't users of the tracker, so they're left out.
    users = [u for u in db.scalars(select(User).order_by(User.last_login_at.desc().nullslast(), User.id))
             if not is_admin(u)]
    ids = [u.id for u in users]
    entries = _counts(db, LogEntry, ids, LogEntry.deleted_at.is_(None))
    foods = _counts(db, UserFood, ids)
    water = _counts(db, WaterLog, ids)
    messages = _counts(db, ChatMessage, ids, ChatMessage.role == "user")
    last_entry = dict(db.execute(
        select(LogEntry.user_id, func.max(LogEntry.created_at)).where(LogEntry.user_id.in_(ids)).group_by(LogEntry.user_id)
    ).all())
    _audit(db, admin, None, "list_users")
    return [
        {
            "id": u.id,
            "email": u.email,
            "preferred_name": u.preferred_name,
            "created_at": _iso(u.created_at),
            "last_login_at": _iso(u.last_login_at),
            "login_count": u.login_count or 0,
            "consented_at": _iso(u.consent_at),
            "onboarded": u.onboarded,
            "goal_type": u.goal_type,
            "entries": entries.get(u.id, 0),
            "foods": foods.get(u.id, 0),
            "water_logs": water.get(u.id, 0),
            "chat_messages": messages.get(u.id, 0),
            "last_logged_at": _iso(last_entry.get(u.id)),
        }
        for u in users
    ]


@router.get("/users/{user_id}")
def user_detail(user_id: int, days: int = 14, admin: User = Depends(admin_user), db: Session = Depends(get_db)):
    user = _target(db, user_id)
    days = max(1, min(days, 90))
    end = local_today(user.timezone)
    weights = db.scalars(
        select(WeightLog).where(WeightLog.user_id == user.id).order_by(WeightLog.logged_at.desc()).limit(20)
    )
    _audit(db, admin, user.id, f"view_user_detail:{days}d")
    return {
        "profile": {**user_to_dict(db, user), "created_at": _iso(user.created_at),
                    "last_login_at": _iso(user.last_login_at), "consented_at": _iso(user.consent_at)},
        "weights": [{"weight_kg": w.weight_kg, "logged_at": _iso(w.logged_at)} for w in weights],
        "days": [d for d in logs_by_day(db, user, end - timedelta(days=days - 1), end) if d["entries"]],
        "foods": [food_to_dict(f, with_ingredients=True) for f in list_foods(db, user.id)],
        "body": body_profile(db, user),
    }


@router.get("/users/{user_id}/chat")
def user_chat(user_id: int, limit: int = 100, admin: User = Depends(admin_user), db: Session = Depends(get_db)):
    user = _target(db, user_id)
    _audit(db, admin, user.id, "view_user_chat")
    return [message_to_dict(m) for m in recent_messages(db, user.id, max(1, min(limit, 500)))]


@router.get("/audit")
def audit_log(limit: int = 100, admin: User = Depends(admin_user), db: Session = Depends(get_db)):
    rows = db.scalars(select(AdminAudit).order_by(AdminAudit.id.desc()).limit(max(1, min(limit, 500))))
    emails = dict(db.execute(select(User.id, User.email)).all())
    return [
        {"at": _iso(r.created_at), "admin": emails.get(r.admin_user_id), "action": r.action,
         "user": emails.get(r.target_user_id) if r.target_user_id else None}
        for r in rows
    ]
