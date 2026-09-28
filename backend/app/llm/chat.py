"""One chat turn: user message -> LLM tool loop -> assistant reply (+ any proposals)."""
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.config import CHAT_HISTORY_MESSAGES, LLM_MAX_TOOL_ROUNDS
from app.llm.prompt import SYSTEM_STABLE, build_dynamic_context
from app.llm.provider import LLMError, get_provider
from app.llm.tools import TOOLS, ToolContext, ToolInputError, run_tool
from app.models import ChatMessage, PendingAction, User
from app.services.actions import action_to_dict, expire_stale, supersede_older

FALLBACK_PROPOSAL_TEXT = "Here's what I've got. Check the card and confirm if it looks right."


def message_to_dict(m: ChatMessage) -> dict:
    return {
        "id": m.id,
        "role": m.role,
        "content": m.content,
        "created_at": m.created_at.isoformat() + "Z",
        "actions": [action_to_dict(a) for a in m.actions],
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
    db: Session, user: User, text: str, feedback_on_action_id: int | None = None
) -> list[dict]:
    """Runs one turn. Returns the new messages (events + assistant reply) for the UI.

    Nothing is committed if the LLM call fails, so the user can simply retry.
    """
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
    reply_text = _run_tool_loop(db, user, history, ctx)

    if not reply_text.strip():
        reply_text = FALLBACK_PROPOSAL_TEXT if ctx.created_actions else "Sorry, I didn't catch that. Could you rephrase?"

    reply = ChatMessage(user_id=user.id, role="assistant", content=reply_text)
    db.add(reply)
    db.flush()
    for a in ctx.created_actions:
        a.chat_message_id = reply.id
    if ctx.created_actions:
        supersede_older(db, user.id, before_id=min(a.id for a in ctx.created_actions))
    db.commit()

    db.refresh(reply)
    return [message_to_dict(m) for m in new_messages] + [message_to_dict(reply)]


def _run_tool_loop(db: Session, user: User, messages: list[dict], ctx: ToolContext) -> str:
    provider = get_provider()
    system_dynamic = build_dynamic_context(db, user)
    texts: list[str] = []

    for _ in range(LLM_MAX_TOOL_ROUNDS):
        resp = provider.complete(
            system_stable=SYSTEM_STABLE,
            system_dynamic=system_dynamic,
            messages=messages,
            tools=TOOLS,
        )
        if resp.text.strip():
            texts.append(resp.text.strip())

        if resp.stop_reason == "refusal":
            return "Sorry, I can't help with that one."
        if resp.stop_reason == "max_tokens" and not resp.tool_calls:
            texts.append("(My reply was cut off. Could you ask again more briefly?)")
            break
        if not resp.tool_calls:
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
        messages.append({"role": "user", "content": results})
    else:
        raise LLMError("The assistant got stuck in a loop. Please try rephrasing.")

    return "\n\n".join(texts)
