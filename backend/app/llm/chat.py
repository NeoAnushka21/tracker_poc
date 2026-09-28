"""One chat turn: user message -> LLM tool loop -> assistant reply (+ any proposals)."""
import re

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.config import CHAT_HISTORY_MESSAGES, LLM_MAX_TOOL_ROUNDS
from app.llm.prompt import SYSTEM_STABLE, build_dynamic_context
from app.llm.provider import LLMError, get_provider
from app.llm.tools import TOOLS, ToolContext, ToolInputError, run_tool
from app.models import ChatMessage, PendingAction, User
from app.services import cancel
from app.services.actions import action_to_dict, expire_stale, supersede_older

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
            out.append({"role": "user", "content": m.content})
    # The API requires the first message to be from the user.
    while out and out[0]["role"] != "user":
        out.pop(0)
    return out


def handle_user_message(
    db: Session, user: User, text: str, feedback_on_action_id: int | None = None,
    request_id: str | None = None,
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

    db.add(ChatMessage(user_id=user.id, role="user", content=text))
    db.flush()

    history = _history_for_llm(recent_messages(db, user.id, CHAT_HISTORY_MESSAGES))
    ctx = ToolContext(db=db, user=user, raw_user_message=text)
    reply_text = _run_tool_loop(db, user, history, ctx, request_id)

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


def _run_tool_loop(db: Session, user: User, messages: list[dict], ctx: ToolContext,
                   request_id: str | None = None) -> str:
    provider = get_provider()
    system_dynamic = build_dynamic_context(db, user)
    texts: list[str] = []
    nudged = False
    water_checked = False

    for _ in range(LLM_MAX_TOOL_ROUNDS):
        resp = provider.complete(
            system_stable=SYSTEM_STABLE,
            system_dynamic=system_dynamic,
            messages=messages,
            tools=TOOLS,
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
        for call in resp.tool_calls:
            try:
                content, is_error = run_tool(ctx, call.name, call.input), False
            except ToolInputError as e:
                content, is_error = f"Error: {e}", True
            results.append({
                "type": "tool_result", "tool_use_id": call.id,
                "content": content, "is_error": is_error,
            })
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
