"""Dashboard "Add food": one AI estimate for a food the user typed that isn't in My Foods.

Same tool, guards and confirm step as the chat: the model can only call propose_entry, and the
pending action it creates is saved by confirm_action when the user presses "Add it". Nothing is
written to the chat history, and the meal and time are the user's picks, not the model's.
"""
import json
from datetime import date

from sqlalchemy.orm import Session

from app.config import LLM_ESCALATE_AFTER_ERRORS, LLM_MAX_TOOL_ROUNDS
from app.llm.pool import get_pool
from app.llm.prompt import build_system_prompt, general_context
from app.llm.provider import LLMError
from app.llm.router import route
from app.llm.tools import TOOLS, ToolContext, ToolInputError, run_tool
from app.models import PendingAction, User, utcnow
from app.services import general_foods, preferences
from app.services.entries import eaten_at_for_meal
from app.services.foods import library_context
from app.timeutil import local_now, utc_to_local

DASHBOARD_RULES = """\
## Dashboard add
- The user added this food from the dashboard's form, not the chat, so they can't answer \
questions. Always call propose_entry, using a standard assumption for anything unclear (a \
medium portion, a typical home recipe) and mention it briefly in the note.
- Keep the user's quantity and unit. Send null for eaten_at and meal_type; the app sets them.
- Only reply without calling the tool if the text isn't a food or drink at all; then say \
why in one short sentence.
"""

_PROPOSE_ENTRY = next(t for t in TOOLS if t["name"] == "propose_entry")


def estimate_food(db: Session, user: User, name: str, quantity: float, unit: str,
                  meal: str, day: date) -> tuple[PendingAction | None, str]:
    """(pending create action, note) or (None, the model's reason it couldn't estimate)."""
    text = f"{quantity:g} {unit} {name}"
    tier = route(text).tier
    ctx = ToolContext(db=db, user=user, raw_user_message=text, match_labels=False)   # no label choices on the dashboard yet
    system = build_system_prompt(["logging", "library"]) + "\n" + DASHBOARD_RULES
    dynamic = "## Current context\n" + json.dumps({
        "now_local": local_now(user.timezone).strftime("%A %Y-%m-%d %H:%M"),
        "my_foods": (my_foods := library_context(db, user, name)) or "(no saved foods match this food)",
        "general_foods": general_context(name, my_foods) or "(none match this food)",
    }, indent=1, ensure_ascii=False)
    messages: list[dict] = [{"role": "user", "content": text}]
    errors, escalated = 0, False

    for _ in range(LLM_MAX_TOOL_ROUNDS):
        resp = get_pool().complete(tier, intent="dashboard_add", escalated=escalated, system_stable=system,
                                   system_dynamic=dynamic, messages=messages, tools=[_PROPOSE_ENTRY])
        if not resp.tool_calls:
            return None, resp.text.strip() or "Couldn't estimate that one."
        messages.append({"role": "assistant", "content": resp.assistant_content})
        results = []
        for call in resp.tool_calls:
            try:
                if call.name != "propose_entry":
                    raise ToolInputError("Only propose_entry is available here")
                content, is_error = run_tool(ctx, call.name, call.input), False
            except ToolInputError as e:
                content, is_error = f"Error: {e}", True
            results.append({"type": "tool_result", "tool_use_id": call.id, "content": content, "is_error": is_error})
        if ctx.created_actions:
            break
        errors += len(results)
        if tier == "small" and errors >= LLM_ESCALATE_AFTER_ERRORS:
            tier, escalated = "large", True
        messages.append({"role": "user", "content": results})
    else:
        raise LLMError("The estimate kept failing validation.")

    action, *extra = ctx.created_actions
    for a in extra:   # one card per add; any repeat call is dropped
        a.status, a.resolved_at = "superseded", utcnow()
    _for_dashboard(db, user, action, meal, day)
    return action, (ctx.notes[0] if ctx.notes else "")


def general_food_action(db: Session, user: User, entry: dict, quantity: float, unit: str,
                        meal: str, day: date) -> tuple[PendingAction, str] | None:
    """A pending action for a general-list food, computed in code (no AI), or None if the unit
    can't be converted (then the AI estimates it instead)."""
    if general_foods.grams_for(entry, quantity, unit) is None:
        return None
    note = (f"From the general food list ({general_foods.SOURCE_NOTE}), plain food with no oil or salt. "
            "Adding it also saves it to My Foods.")
    if heads_up := preferences.allergen_note(user, [general_foods.display_name(entry)]):
        note += " " + heads_up
    ctx = ToolContext(db=db, user=user, raw_user_message=f"{quantity:g} {unit} {entry['name']}")
    item = {"ingredient_name": general_foods.display_name(entry), "brand_name": None, "quantity": quantity,
            "unit": unit, "calories": 0, "protein_g": 0, "carbs_g": 0, "fat_g": 0, "fiber_g": 0, "food_id": None,
            "general_id": entry["id"], "unit_weight_g": None, "micronutrients": None}
    try:
        run_tool(ctx, "propose_entry", {"summary": general_foods.display_name(entry), "eaten_at": None,
                                        "meal_type": None, "items": [item], "note": note})
    except ToolInputError:
        return None
    action = ctx.created_actions[0]
    _for_dashboard(db, user, action, meal, day)
    return action, note


def _for_dashboard(db: Session, user: User, action: PendingAction, meal: str, day: date) -> None:
    """The user's meal and time, and the dashboard origin (kept apart from chat proposals)."""
    eaten_utc = eaten_at_for_meal(db, user, meal, day)
    action.payload = {
        **action.payload,
        "origin": "dashboard",
        "meal_type": meal,
        "meal_type_source": "stated",
        "eaten_at": utc_to_local(eaten_utc, user.timezone).strftime("%Y-%m-%dT%H:%M"),
        "eaten_at_utc": eaten_utc.isoformat(),
    }
