"""Admin panel API: read-only access to users and the data they've shared.

Access is limited to ADMIN_EMAILS, and every view of a user's data is written to
admin_audit so there's a record of who looked at what.
"""
import uuid
from datetime import timedelta

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app import config
from app.db import get_db
from app.deps import admin_user, is_admin
from app.llm.chat import message_to_dict, recent_messages
from app.models import (
    AdminAudit, ChatMessage, LlmUsage, LogEntry, User, UserFood, WaitlistEntry, WaterLog, WeightLog, utcnow,
)
from app.routers.profile import body_profile, user_to_dict
from app.services.foods import food_to_dict, list_foods
from app.services.logs import logs_by_day
from app.timeutil import local_today
from app.schemas import TotpCodeIn, TotpDisableIn
from app.security import verify_password
from app.services import email, totp
from app.services import waitlist as wl

router = APIRouter(prefix="/api/admin", tags=["admin"])


def _iso(dt) -> str | None:
    return dt.isoformat() + "Z" if dt else None


def _audit(db: Session, admin: User, target_id: int | None, action: str) -> None:
    db.add(AdminAudit(admin_user_id=admin.id, target_user_id=target_id, action=action))
    db.commit()


def _target(db: Session, public_id: uuid.UUID) -> User:
    user = db.scalar(select(User).where(User.public_id == public_id))
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
            "id": str(u.public_id),
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
def user_detail(user_id: uuid.UUID, days: int = 14, admin: User = Depends(admin_user), db: Session = Depends(get_db)):
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
def user_chat(user_id: uuid.UUID, limit: int = 100, admin: User = Depends(admin_user), db: Session = Depends(get_db)):
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


@router.get("/llm-usage")
def llm_usage(hours: int = 24, admin: User = Depends(admin_user), db: Session = Depends(get_db)):
    """Model calls, tokens and quota state (aggregate only: no user data, so not audited)."""
    from app.llm.pool import get_pool
    from app.llm.provider import LLMError

    hours = max(1, min(hours, 24 * 30))
    since = utcnow() - timedelta(hours=hours)
    rows = list(db.scalars(select(LlmUsage).where(LlmUsage.created_at >= since)))
    by_model: dict[tuple, dict] = {}
    by_intent: dict[str, dict] = {}
    for r in rows:
        if r.outcome == "fastpath":
            continue
        m = by_model.setdefault((r.provider, r.model, r.tier), {
            "provider": r.provider, "model": r.model, "tier": r.tier, "calls": 0, "ok": 0, "errors": 0,
            "rate_limited": 0, "prompt_tokens": 0, "completion_tokens": 0, "_latency": []})
        m["calls"] += 1
        m[{"ok": "ok", "error": "errors", "rate_limited": "rate_limited"}.get(r.outcome, "errors")] += 1
        m["prompt_tokens"] += r.prompt_tokens or 0
        m["completion_tokens"] += r.completion_tokens or 0
        if r.outcome == "ok" and r.latency_ms is not None:
            m["_latency"].append(r.latency_ms)
        i = by_intent.setdefault(r.intent, {"intent": r.intent, "calls": 0, "tokens": 0})
        i["calls"] += 1
        i["tokens"] += (r.prompt_tokens or 0) + (r.completion_tokens or 0)
    for m in by_model.values():
        lat = m.pop("_latency")
        m["avg_latency_ms"] = round(sum(lat) / len(lat)) if lat else None
    fast = [r for r in rows if r.outcome == "fastpath"]
    user_messages = db.scalar(select(func.count()).select_from(ChatMessage).where(
        ChatMessage.role == "user", ChatMessage.created_at >= since)) or 0
    model_calls = sum(m["calls"] for m in by_model.values())
    try:
        pool = get_pool().status()
    except LLMError as e:
        pool = [{"error": str(e)}]
    return {
        "hours": hours,
        "totals": {
            "user_messages": user_messages,
            "model_calls": model_calls,
            "fastpath_replies": len(fast),
            "fastpath_share_pct": round(100 * len(fast) / user_messages) if user_messages else None,
            "tokens": sum(m["prompt_tokens"] + m["completion_tokens"] for m in by_model.values()),
            "errors": sum(m["errors"] for m in by_model.values()),
            "rate_limited": sum(m["rate_limited"] for m in by_model.values()),
            "escalations": sum(1 for r in rows if r.escalated and r.outcome == "ok"),
        },
        "by_model": sorted(by_model.values(), key=lambda m: (-m["calls"], m["model"])),
        "by_intent": sorted(by_intent.values(), key=lambda i: -i["calls"]),
        "fastpath": {name: sum(1 for r in fast if r.model == name) for name in sorted({r.model for r in fast})},
        "pool": pool,
    }


# --- waitlist ("Join the community" while sign-up is by invitation) -----------------------------

def _waitlist_row(e: WaitlistEntry, has_account: bool) -> dict:
    return {"id": str(e.public_id), "email": e.email, "name": e.name, "interest": e.interest,
            "created_at": _iso(e.created_at), "approved_at": _iso(e.approved_at), "has_account": has_account}


def _waitlist_entry(db: Session, entry_id: uuid.UUID) -> WaitlistEntry:
    entry = db.scalar(select(WaitlistEntry).where(WaitlistEntry.public_id == entry_id))
    if entry is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Not on the waitlist")
    return entry


@router.get("/waitlist")
def waitlist(admin: User = Depends(admin_user), db: Session = Depends(get_db)):
    """Everyone on the list, newest first, and whether each has made an account yet."""
    entries = list(db.scalars(select(WaitlistEntry).order_by(WaitlistEntry.created_at.desc(), WaitlistEntry.id.desc())))
    emails = [e.email for e in entries]
    with_account = set(db.scalars(select(User.email).where(User.email.in_(emails)))) if emails else set()
    _audit(db, admin, None, "view_waitlist")
    return {"join_mode": config.JOIN_MODE, "email_enabled": email.enabled(),
            "entries": [_waitlist_row(e, e.email in with_account) for e in entries]}


@router.post("/waitlist/{entry_id}/approve")
def approve_waitlist(entry_id: uuid.UUID, background: BackgroundTasks, admin: User = Depends(admin_user),
                     db: Session = Depends(get_db)):
    """Let this email create an account, and email them the invitation (sent again if pressed again)."""
    entry = _waitlist_entry(db, entry_id)
    entry.approved_at = entry.approved_at or utcnow()
    _audit(db, admin, None, f"waitlist approved: {entry.email}")
    background.add_task(email.send, entry.email, f"You're in: your {config.APP_NAME} invitation", wl.invite_text(entry))
    has_account = db.scalar(select(User.id).where(User.email == entry.email)) is not None
    return _waitlist_row(entry, has_account)


@router.delete("/waitlist/{entry_id}")
def remove_waitlist(entry_id: uuid.UUID, admin: User = Depends(admin_user), db: Session = Depends(get_db)):
    """Take someone off the list (e.g. they asked to be removed). An account they made stays."""
    entry = _waitlist_entry(db, entry_id)
    db.delete(entry)
    _audit(db, admin, None, f"waitlist removed: {entry.email}")
    return {"ok": True}


# --- two-step sign-in for the admin account ------------------------------------------------

@router.get("/totp")
def totp_status(admin: User = Depends(admin_user)):
    return {"enabled": totp.enabled(admin)}


@router.post("/totp/setup")
def totp_setup(admin: User = Depends(admin_user), db: Session = Depends(get_db)):
    """A new secret to scan; it takes effect only after a correct code (POST /totp/enable)."""
    if totp.enabled(admin):
        raise HTTPException(status.HTTP_409_CONFLICT, "Two-step sign-in is already on")
    secret = totp.new_secret()
    admin.totp_secret, admin.totp_last_step = totp.seal(secret), None
    db.commit()
    return totp.provisioning(secret, admin.email)


@router.post("/totp/enable")
def totp_enable(body: TotpCodeIn, admin: User = Depends(admin_user), db: Session = Depends(get_db)):
    if totp.enabled(admin):
        raise HTTPException(status.HTTP_409_CONFLICT, "Two-step sign-in is already on")
    if not totp.verify(admin, body.code):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, f"That code isn't right. Check the entry for {config.APP_NAME} in your authenticator app and try the current code.")
    admin.totp_enabled_at = utcnow()
    _audit(db, admin, None, "two-step sign-in turned on")
    db.commit()
    return {"enabled": True}


@router.post("/totp/disable")
def totp_disable(body: TotpDisableIn, admin: User = Depends(admin_user), db: Session = Depends(get_db)):
    if not totp.enabled(admin):
        return {"enabled": False}
    if not verify_password(body.password, admin.hashed_password) or not totp.verify(admin, body.code):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Password or code is wrong")
    admin.totp_secret = admin.totp_enabled_at = admin.totp_last_step = None
    _audit(db, admin, None, "two-step sign-in turned off")
    db.commit()
    return {"enabled": False}
