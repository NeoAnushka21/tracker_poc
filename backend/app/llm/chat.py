"""One chat turn: user message -> LLM tool loop -> assistant reply (+ any proposals)."""
import re
from datetime import date, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.config import (
    CHAT_DAY_GRACE_HOURS, CHAT_HISTORY_MESSAGES, LLM_ESCALATE_AFTER_ERRORS, LLM_FASTPATH, LLM_MAX_TOOL_ROUNDS,
    LLM_ROUTING, LLM_SMALL_HISTORY_MESSAGES,
)
from app.llm import usage
from app.llm.fastpath import try_fastpath
from app.llm.pool import get_pool
from app.llm.prompt import build_dynamic_context, build_system_prompt
from app.llm.provider import LLMError
from app.llm.router import ALL_TOOLS, SECTIONS, Route, escalate, route
from app.llm.tools import TOOLS, ToolContext, ToolInputError, run_tool
from app.models import ChatMessage, PendingAction, User, utcnow
from app.services import allowance, cancel
from app.services.actions import action_to_dict, expire_stale, open_actions, supersede_older
from app.timeutil import local_day_bounds_utc, local_today, utc_to_local

PROPOSE_TOOLS = {"propose_entry", "propose_edit", "propose_delete", "propose_recipe", "propose_water", "propose_move"}
FALLBACK_PROPOSAL_TEXT = "Here's what I've got. Check the card and confirm if it looks right."

# The model sometimes claims it saved something without calling a propose_* tool.
FALSE_WRITE_CLAIM = re.compile(
    r"^\s*(?:logged|saved|added|recorded|created)\b"
    r"|\bI(?:'ve| have)?\s+(?:just\s+)?(?:logged|saved|added|recorded|created)\b",
    re.I,
)
FALSE_CLAIM_NUDGE = (
    "[App check] Your reply says you logged or saved something, but you didn't call a propose_* "
    "tool, so nothing was created and the user can't confirm anything. If the user described food "
    "they ate or asked to save a recipe, call the right propose_* tool now (put any question or "
    "offer in its note). Otherwise, rewrite your reply without claiming anything was saved."
)
# Proposal notes should read as "not saved yet"; soften a leading "Logged ..." etc.
SAVED_OPENER = re.compile(
    r"^\s*(?:I(?:'ve| have|'m| am)?\s+)?(?:logged|saved|added|recorded|created|logging|saving|adding)\b", re.I
)


WATER_MENTION = re.compile(r"\bwater\b", re.I)
WATER_NUDGE = (
    "[App check] The user's message also mentions water, but there's no propose_water card. "
    "If they drank plain water, call propose_water for it now. If not (e.g. coconut water, "
    "or water only used in cooking), don't call anything; just reply with a short note."
)


def _missed_water(ctx: ToolContext) -> bool:
    return bool(WATER_MENTION.search(ctx.raw_user_message)) and not any(
        a.action_type == "water" for a in ctx.created_actions
    )


def _unsaved_wording(note: str) -> str:
    return SAVED_OPENER.sub("Here's", note, count=1)


def message_to_dict(m: ChatMessage) -> dict:
    return {
        "id": m.id,
        "role": m.role,
        "content": m.content,
        "created_at": m.created_at.isoformat() + "Z",
        "actions": [action_to_dict(a) for a in m.actions],
        "kind": m.kind,
        "data": m.data,
    }


def recent_messages(db: Session, user_id: int, limit: int) -> list[ChatMessage]:
    stmt = (
        select(ChatMessage)
        .where(ChatMessage.user_id == user_id)
        .options(selectinload(ChatMessage.actions))
        .order_by(ChatMessage.id.desc())
        .limit(limit)
    )
    return list(reversed(db.scalars(stmt).all()))


def messages_for_day(db: Session, user: User, day: date) -> tuple[list[ChatMessage], date | None]:
    """The chat for one local day, plus the most recent earlier day that has messages."""
    start, end = local_day_bounds_utc(day, user.timezone)
    msgs = list(db.scalars(
        select(ChatMessage)
        .where(ChatMessage.user_id == user.id, ChatMessage.created_at >= start, ChatMessage.created_at < end)
        .options(selectinload(ChatMessage.actions))
        .order_by(ChatMessage.id)
    ))
    earlier = db.scalars(
        select(ChatMessage.created_at)
        .where(ChatMessage.user_id == user.id, ChatMessage.created_at < start)
        .order_by(ChatMessage.created_at.desc()).limit(1)
    ).first()
    return msgs, (utc_to_local(earlier, user.timezone).date() if earlier else None)


def _todays_messages(db: Session, user: User, limit: int) -> list[ChatMessage]:
    """What the model sees: today's chat (fresh each day) plus a short grace window before
    midnight, capped at `limit` messages."""
    start, _ = local_day_bounds_utc(local_today(user.timezone), user.timezone)
    since = min(start, utcnow() - timedelta(hours=CHAT_DAY_GRACE_HOURS))
    return [m for m in recent_messages(db, user.id, limit) if m.created_at >= since]


def _history_for_llm(messages: list[ChatMessage]) -> list[dict]:
    """Stored chat -> API messages. Proposals and app events are rendered as text notes."""
    out: list[dict] = []
    for m in messages:
        if m.kind == "progress":
            continue   # the day's totals are already in the per-turn context
        if m.role == "assistant":
            text = m.content
            for a in m.actions:
                text += (
                    f"\n[Proposal #{a.id} ({a.action_type}): {a.payload.get('summary')}"
                    f" | total {a.payload.get('totals', {}).get('calories', '-')} kcal"
                    f" | status: {a.status}]"
                )
            out.append({"role": "assistant", "content": text})
        elif m.role == "event":
            out.append({"role": "user", "content": f"[App event] {m.content}"})
        else:
            picked = (m.data or {}).get("log_date")
            prefix = f"[Date picked in the app: {picked}] " if picked else ""
            out.append({"role": "user", "content": prefix + m.content})
    # The API requires the first message to be from the user.
    while out and out[0]["role"] != "user":
        out.pop(0)
    return out


def handle_user_message(
    db: Session, user: User, text: str, feedback_on_action_id: int | None = None,
    request_id: str | None = None, log_date: date | None = None,
) -> list[dict]:
    """Runs one turn. Returns the new messages (events + assistant reply) for the UI.

    Nothing is committed if the LLM call fails, so the user can simply retry.
    """
    cancel.start(user.id, request_id)
    expire_stale(db, user.id)
    new_messages: list[ChatMessage] = []

    if feedback_on_action_id is not None:
        action = db.get(PendingAction, feedback_on_action_id)
        if action and action.user_id == user.id and action.status == "pending":
            ev = ChatMessage(
                user_id=user.id, role="event",
                content=f"User clicked 'Needs changes' on proposal #{action.id}; their feedback follows.",
            )
            db.add(ev)
            new_messages.append(ev)

    today = local_today(user.timezone)
    if log_date is not None and log_date >= today:
        log_date = None   # today (or a future date) is the default, not a selection
    user_msg = ChatMessage(user_id=user.id, role="user", content=text,
                           data={"log_date": log_date.isoformat()} if log_date else None)
    db.add(user_msg)
    db.flush()
    new_messages.append(user_msg)

    ctx = ToolContext(db=db, user=user, raw_user_message=text)
    fast = None
    if LLM_FASTPATH and feedback_on_action_id is None and log_date is None:
        fast = try_fastpath(db, user, text, ctx)
    if fast is not None:
        handler, reply_text = fast
        usage.record(provider="fastpath", model=handler, tier="none", intent=handler, prompt_tokens=0,
                     completion_tokens=0, latency_ms=0, outcome="fastpath", escalated=False)
    else:
        allowance.check(db, user)   # before any model call; raises AllowanceExceeded
        r = (route(text, feedback=feedback_on_action_id is not None) if LLM_ROUTING
             else Route("full", "large", ALL_TOOLS, SECTIONS["full"], "routing off"))
        todays = _todays_messages(db, user, LLM_SMALL_HISTORY_MESSAGES if r.tier == "small" else CHAT_HISTORY_MESSAGES)
        food_text = " ".join([text] + [m.content for m in todays if m.role == "user"][-3:]
                             + _open_proposal_food_names(db, user))
        reply_text = _run_tool_loop(db, user, _history_for_llm(todays), ctx, request_id, log_date, r, food_text)
        allowance.record(db, user, "chat")   # committed with the reply below; failures don't count

    if not reply_text.strip():
        reply_text = FALLBACK_PROPOSAL_TEXT if ctx.created_actions else "Sorry, I didn't catch that. Could you rephrase?"

    reply = ChatMessage(user_id=user.id, role="assistant", content=reply_text)
    db.add(reply)
    db.flush()
    for a in ctx.created_actions:
        a.chat_message_id = reply.id
    if ctx.created_actions:
        supersede_older(db, user.id, before_id=min(a.id for a in ctx.created_actions))
    cancel.finish_or_cancelled(user.id, request_id)   # last point where Stop can still discard the turn
    db.commit()

    db.refresh(reply)
    return [message_to_dict(m) for m in new_messages] + [message_to_dict(reply)]


def _open_proposal_food_names(db: Session, user: User) -> list[str]:
    """Food names on pending cards, so feedback like "make it 3" still sees those saved foods."""
    names = []
    for a in open_actions(db, user.id):
        names += [i.get("ingredient_name", "") for i in (a.payload.get("items") or [])]
    return names


def _tools_for(r: Route) -> list[dict]:
    return TOOLS if r.tools is ALL_TOOLS else [t for t in TOOLS if t["name"] in r.tools]


def _run_tool_loop(db: Session, user: User, messages: list[dict], ctx: ToolContext,
                   request_id: str | None = None, log_date: date | None = None,
                   r: Route | None = None, food_text: str | None = None) -> str:
    pool = get_pool()
    r = r or Route("full", "large", ALL_TOOLS, SECTIONS["full"], "default")
    # Data questions don't need the food library at all.
    system_dynamic = build_dynamic_context(db, user, log_date, "" if r.intent == "query" else food_text)
    texts: list[str] = []
    nudged = False
    water_checked = False
    validation_errors = 0
    escalated = False

    for _ in range(LLM_MAX_TOOL_ROUNDS):
        resp = pool.complete(
            r.tier, intent=r.intent, escalated=escalated,
            system_stable=build_system_prompt(r.sections),
            system_dynamic=system_dynamic,
            messages=messages,
            tools=_tools_for(r),
        )
        cancel.raise_if_cancelled(user.id, request_id)
        if resp.text.strip():
            texts.append(resp.text.strip())

        if resp.stop_reason == "refusal":
            return "Sorry, I can't help with that one."
        if resp.stop_reason == "max_tokens" and not resp.tool_calls:
            texts.append("(My reply was cut off. Could you ask again more briefly?)")
            break
        if not resp.tool_calls:
            if not ctx.created_actions and not nudged and FALSE_WRITE_CLAIM.search(resp.text):
                # Claimed a write that never happened: send it back once to fix itself.
                nudged = True
                if texts and texts[-1] == resp.text.strip():
                    texts.pop()
                messages.append({"role": "assistant", "content": resp.text})
                messages.append({"role": "user", "content": FALSE_CLAIM_NUDGE})
                continue
            break

        messages.append({"role": "assistant", "content": resp.assistant_content})
        results = []
        offered = {t["name"] for t in _tools_for(r)}
        for call in resp.tool_calls:
            try:
                # Only the tools offered for this message may run, even if the model names another one.
                if call.name not in offered:
                    raise ToolInputError(f"The tool '{call.name}' isn't available for this message")
                content, is_error = run_tool(ctx, call.name, call.input), False
            except ToolInputError as e:
                content, is_error = f"Error: {e}", True
            results.append({
                "type": "tool_result", "tool_use_id": call.id,
                "content": content, "is_error": is_error,
            })
        validation_errors += sum(1 for x in results if x["is_error"])
        if r.tier == "small" and validation_errors >= LLM_ESCALATE_AFTER_ERRORS:
            # The small model keeps producing invalid calls: let the large one finish the turn.
            r, escalated = escalate(r), True
        # A round of only successful proposals ends the turn: the card plus the tool's
        # `note` is the reply, which saves a model call per logged meal.
        if all(c.name in PROPOSE_TOOLS for c in resp.tool_calls) and not any(r["is_error"] for r in results):
            if not water_checked and _missed_water(ctx):
                # Food was proposed but water the user mentioned wasn't: ask once.
                water_checked = True
                messages.append({"role": "user", "content": results + [{"type": "text", "text": WATER_NUDGE}]})
                continue
            break
        messages.append({"role": "user", "content": results})
    else:
        raise LLMError("The assistant got stuck in a loop. Please try rephrasing.")

    # Proposal notes lead the reply (including when a later check round ended in plain text).
    if ctx.notes:
        texts = [_unsaved_wording(n) for n in ctx.notes] + texts

    return "\n\n".join(texts)
