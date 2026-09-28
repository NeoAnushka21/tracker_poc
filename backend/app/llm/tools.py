"""Tools the LLM may call. It touches data only through these; it never writes SQL.

propose_* tools only create a PendingAction (shown to the user as a card).
get_* tools are read-only over confirmed entries.
"""
import json
import re
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone

from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.config import LEGACY_SNACK, MEAL_TYPES, MICRONUTRIENTS, WATER_MAX_LOG_ML
from app.models import PendingAction, User, utcnow
from app.schemas import ItemIn
from app.services.foods import (
    FoodError, compute_recipe, find_by_name, food_to_dict, get_user_food, resolve_library_item,
)
from app.services.logs import (
    daily_summary, entry_to_dict, get_active_entry, logs_by_day, sum_items,
)
from app.timeutil import infer_meal_type, local_to_utc, resolve_meal_type, utc_to_local

MAX_QUERY_DAYS = 31

def _nullable(schema: dict, description: str) -> dict:
    return {"anyOf": [schema, {"type": "null"}], "description": description}


_MICROS_SCHEMA = {
    "type": "object",
    "description": (
        "Best estimate of these micronutrients for this item's amount (not per 100 g); "
        "null for any you can't reasonably estimate."
    ),
    "properties": {
        key: _nullable({"type": "number"}, f"{label} in {unit}") for key, label, unit, _, _ in MICRONUTRIENTS
    },
    "required": [m[0] for m in MICRONUTRIENTS],
    "additionalProperties": False,
}

_ITEM_SCHEMA = {
    "type": "object",
    "properties": {
        "ingredient_name": {"type": "string", "description": "Food name only, no amount, e.g. 'chicken breast, cooked'"},
        "brand_name": _nullable({"type": "string"}, "Brand if the user named one, else null"),
        "quantity": {"type": "number"},
        "unit": {"type": "string", "description": "g, ml, piece, cup, tbsp, slice, scoop..."},
        "calories": {"type": "number"},
        "protein_g": {"type": "number"},
        "carbs_g": {"type": "number"},
        "fat_g": {"type": "number"},
        "fiber_g": {"type": "number"},
        "food_id": _nullable(
            {"type": "integer"},
            "Id from the user's food library when this item is one of their saved foods or recipes; "
            "the app then computes the nutrients itself (send 0 for them). null for a new estimate.",
        ),
        "unit_weight_g": _nullable(
            {"type": "number"},
            "Approximate grams in ONE unit when the unit isn't g/ml (e.g. 1 almond = 1.2, 1 chapati = 40, "
            "1 cup cooked rice = 160), else null.",
        ),
        "micronutrients": _MICROS_SCHEMA,
    },
    "required": [
        "ingredient_name", "brand_name", "quantity", "unit",
        "calories", "protein_g", "carbs_g", "fat_g", "fiber_g", "food_id", "unit_weight_g", "micronutrients",
    ],
    "additionalProperties": False,
}

# "snack" is accepted when the user doesn't say which; the app picks morning/evening by time.
_MEAL_TYPE = {"type": "string", "enum": MEAL_TYPES + [LEGACY_SNACK]}

_NOTE = {
    "type": "string",
    "description": (
        "Your reply to the user, shown above the card: 1-2 plain-text sentences mentioning any "
        "assumptions, e.g. 'Here's your guava. I assumed one medium one, about 150 g.' It is "
        "not saved yet, so never say 'logged', 'saved' or 'added'. Your turn ends after proposing."
    ),
}

TOOLS = [
    {
        "name": "propose_entry",
        "description": (
            "Propose a new food log entry for the user to confirm. Nothing is saved until the "
            "user clicks Confirm on the card this creates. Use one call per meal/occasion."
        ),
        "strict": True,
        "input_schema": {
            "type": "object",
            "properties": {
                "summary": {"type": "string", "description": "Short human-readable description, e.g. 'Chicken & onion stir-fry'"},
                "eaten_at": _nullable(
                    {"type": "string"},
                    "When it was eaten, user's local time 'YYYY-MM-DDTHH:MM'. null = just now.",
                ),
                "meal_type": _nullable(
                    _MEAL_TYPE,
                    "Only set if the user explicitly said which meal it was; otherwise null and the app infers it from the time.",
                ),
                "items": {"type": "array", "items": _ITEM_SCHEMA},
                "note": _NOTE,
            },
            "required": ["summary", "eaten_at", "meal_type", "items", "note"],
            "additionalProperties": False,
        },
    },
    {
        "name": "propose_edit",
        "description": (
            "Propose changing an existing confirmed log entry. `items` is the complete new list "
            "of items for the entry (not a diff). Nothing changes until the user confirms."
        ),
        "strict": True,
        "input_schema": {
            "type": "object",
            "properties": {
                "entry_id": {"type": "integer"},
                "summary": {"type": "string", "description": "What is changing, e.g. 'Chicken 100g → 150g'"},
                "eaten_at": _nullable({"type": "string"}, "New local time 'YYYY-MM-DDTHH:MM', or null to keep"),
                "meal_type": _nullable(_MEAL_TYPE, "New meal type, or null to keep"),
                "items": {"type": "array", "items": _ITEM_SCHEMA},
                "note": _NOTE,
            },
            "required": ["entry_id", "summary", "eaten_at", "meal_type", "items", "note"],
            "additionalProperties": False,
        },
    },
    {
        "name": "propose_delete",
        "description": "Propose deleting an existing confirmed log entry. Nothing is deleted until the user confirms.",
        "strict": True,
        "input_schema": {
            "type": "object",
            "properties": {
                "entry_id": {"type": "integer"},
                "summary": {"type": "string", "description": "What is being deleted"},
                "note": _NOTE,
            },
            "required": ["entry_id", "summary", "note"],
            "additionalProperties": False,
        },
    },
    {
        "name": "propose_recipe",
        "description": (
            "Propose saving (or replacing) one of the user's recipes: raw ingredients for a whole batch "
            "plus its yield. The app computes nutrients per piece / per 100 g / per serving. Only when the "
            "user asks or agrees to save a recipe. Nothing is saved until they confirm."
        ),
        "strict": True,
        "input_schema": {
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "Recipe name as the user calls it, e.g. 'Chapati', 'Lauki sabzi'"},
                "ingredients": {"type": "array", "items": _ITEM_SCHEMA,
                                "description": "Raw ingredients for the WHOLE batch, with their nutrients (or food_id)."},
                "yield_pieces": _nullable({"type": "number"}, "How many pieces the batch makes (chapatis, idlis), else null"),
                "yield_servings": _nullable({"type": "number"}, "How many servings the batch makes, else null"),
                "cooked_weight_g": _nullable({"type": "number"}, "Weight of the whole cooked batch in grams, if known, else null"),
                "note": _NOTE,
            },
            "required": ["name", "ingredients", "yield_pieces", "yield_servings", "cooked_weight_g", "note"],
            "additionalProperties": False,
        },
    },
    {
        "name": "propose_water",
        "description": (
            "Propose logging plain drinking water to the separate water tracker (not a food entry). "
            "Nothing is saved until the user confirms."
        ),
        "strict": True,
        "input_schema": {
            "type": "object",
            "properties": {
                "amount_ml": {"type": "number", "description": "Total ml (1 glass = 250 ml, 1 litre = 1000 ml)"},
                "drank_at": _nullable({"type": "string"}, "Local time 'YYYY-MM-DDTHH:MM' if not just now, else null"),
                "note": _NOTE,
            },
            "required": ["amount_ml", "drank_at", "note"],
            "additionalProperties": False,
        },
    },
    {
        "name": "get_food",
        "description": "Get one saved food or recipe from the user's library (a recipe includes its ingredients).",
        "strict": True,
        "input_schema": {
            "type": "object",
            "properties": {"food_id": {"type": "integer"}},
            "required": ["food_id"],
            "additionalProperties": False,
        },
    },
    {
        "name": "get_logs",
        "description": (
            f"Get confirmed log entries (with ids, items and per-day totals) for a local date range, "
            f"inclusive. Max {MAX_QUERY_DAYS} days per call."
        ),
        "strict": True,
        "input_schema": {
            "type": "object",
            "properties": {
                "start_date": {"type": "string", "description": "YYYY-MM-DD"},
                "end_date": {"type": "string", "description": "YYYY-MM-DD"},
            },
            "required": ["start_date", "end_date"],
            "additionalProperties": False,
        },
    },
    {
        "name": "get_daily_summary",
        "description": "Get one local day's totals vs targets, remaining budget, and its entries.",
        "strict": True,
        "input_schema": {
            "type": "object",
            "properties": {"date": {"type": "string", "description": "YYYY-MM-DD"}},
            "required": ["date"],
            "additionalProperties": False,
        },
    },
]


class ToolInputError(Exception):
    pass


@dataclass
class ToolContext:
    db: Session
    user: User
    raw_user_message: str
    created_actions: list[PendingAction] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)   # user-facing text from propose_* calls


def run_tool(ctx: ToolContext, name: str, args: dict) -> str:
    """Execute a tool call. Returns the tool_result text; raises ToolInputError on bad input."""
    handler = _HANDLERS.get(name)
    if handler is None:
        raise ToolInputError(f"Unknown tool '{name}'")
    if "__invalid_json__" in args:
        raise ToolInputError("Arguments were not valid JSON; call the tool again with valid JSON")
    # Non-strict providers can send missing or wrongly-typed fields; report, don't crash.
    try:
        return json.dumps(handler(ctx, args))
    except KeyError as e:
        raise ToolInputError(f"Missing required argument {e}") from e
    except (TypeError, AttributeError) as e:
        raise ToolInputError(f"Argument has the wrong type: {e}") from e


# --- helpers ---------------------------------------------------------------

def _parse_items(ctx: ToolContext, raw_items: list, what: str = "items") -> list[dict]:
    """Validate proposed items. Library items get nutrients computed from the saved food;
    new estimates are sanity-checked (calories vs macros)."""
    if not raw_items:
        raise ToolInputError(f"{what} must contain at least one item")
    try:
        items = [ItemIn.model_validate(i).model_dump() for i in raw_items]
    except ValidationError as e:
        raise ToolInputError(f"Invalid item: {e.errors()[0]['msg']}") from e
    resolved, estimates = [], []
    for it in items:
        if it.get("food_id"):
            try:
                resolved.append(resolve_library_item(ctx.db, ctx.user, it))
            except FoodError as e:
                raise ToolInputError(str(e)) from e
            continue
        for k in ("calories", "protein_g", "carbs_g", "fat_g", "fiber_g"):
            it[k] = round(it[k], 1)
        it["ingredient_name"] = strip_leading_quantity(it["ingredient_name"], it["quantity"])
        it["source"] = "estimate"
        resolved.append(it)
        estimates.append(it)
    _check_energy_balance(estimates)
    return resolved


_LEADING_QTY = re.compile(r"^\s*(\d+(?:[.,]\d+)?)\s*(?:g|gm|gms|grams?|kg|ml|l|pcs?|pieces?|x)?\s+", re.I)


def strip_leading_quantity(name: str, quantity: float) -> str:
    """'50 g brown rice' -> 'brown rice', but only when the number is this item's own
    quantity, so names like '7 grain bread' are left alone."""
    m = _LEADING_QTY.match(name)
    if m and float(m.group(1).replace(",", ".")) == quantity:
        rest = name[m.end():].strip()
        return rest or name
    return name


_ALCOHOL_WORDS = ("beer", "wine", "vodka", "whisk", "rum", "gin", "tequila", "brandy",
                  "liquor", "liqueur", "cocktail", "sake", "cider", "alcohol")
ENERGY_TOLERANCE = 0.25      # allowed gap between stated kcal and 4/4/9 macro kcal
ENERGY_MIN_KCAL = 40         # below this, rounding noise dominates


def _check_energy_balance(items: list[dict]) -> None:
    """Catch estimates whose calories don't match their macros (e.g. a quantity was
    scaled for calories but not protein). Alcohol carries its own 7 kcal/g, so skip it."""
    bad = []
    for it in items:
        name = it["ingredient_name"].lower()
        if it["calories"] < ENERGY_MIN_KCAL or any(w in name for w in _ALCOHOL_WORDS):
            continue
        macro_kcal = 4 * it["protein_g"] + 4 * it["carbs_g"] + 9 * it["fat_g"]
        if abs(macro_kcal - it["calories"]) > ENERGY_TOLERANCE * it["calories"]:
            bad.append(f"{it['quantity']:g} {it['unit']} {it['ingredient_name']}: "
                       f"{it['calories']:g} kcal stated but macros give {macro_kcal:.0f} kcal")
    if bad:
        raise ToolInputError(
            "Calories and macros don't agree (protein 4, carbs 4, fat 9 kcal/g) for: "
            + "; ".join(bad)
            + ". Recalculate all nutrients for these quantities and call the tool again."
        )


def _parse_local_dt(s: str, tz_name: str) -> datetime:
    """Model-supplied local time -> naive UTC."""
    try:
        dt = datetime.fromisoformat(s)
    except ValueError as e:
        raise ToolInputError(f"eaten_at '{s}' is not in YYYY-MM-DDTHH:MM format") from e
    if dt.tzinfo is not None:
        dt_utc = dt.astimezone(timezone.utc).replace(tzinfo=None)
    else:
        dt_utc = local_to_utc(dt, tz_name)
    if dt_utc > utcnow() + timedelta(minutes=10):
        raise ToolInputError("eaten_at is in the future; ask the user when they ate it")
    return dt_utc


def _parse_date(s: str) -> date:
    try:
        return date.fromisoformat(s)
    except ValueError as e:
        raise ToolInputError(f"'{s}' is not a YYYY-MM-DD date") from e


def _add_action(ctx: ToolContext, action_type: str, payload: dict, target_entry_id: int | None,
                note: str | None) -> dict:
    if note and note.strip():
        ctx.notes.append(note.strip())
    action = PendingAction(
        user_id=ctx.user.id,
        action_type=action_type,
        target_entry_id=target_entry_id,
        payload=payload,
    )
    ctx.db.add(action)
    ctx.db.flush()
    ctx.created_actions.append(action)
    return {
        "proposal_id": action.id,
        "status": "shown_to_user_awaiting_confirmation",
        "info": "The user sees a card with Confirm / Needs changes / Cancel. Nothing is saved until they click Confirm.",
    }


def _entry_or_error(ctx: ToolContext, entry_id: int):
    entry = get_active_entry(ctx.db, ctx.user.id, entry_id)
    if entry is None:
        raise ToolInputError(f"No log entry #{entry_id} found (it may have been deleted). Use get_logs to find the right id.")
    return entry


# --- handlers --------------------------------------------------------------

def _propose_entry(ctx: ToolContext, args: dict) -> dict:
    tz = ctx.user.timezone
    items = _parse_items(ctx, args.get("items") or [])
    eaten_utc = _parse_local_dt(args["eaten_at"], tz) if args.get("eaten_at") else utcnow()
    eaten_local = utc_to_local(eaten_utc, tz)
    stated = args.get("meal_type")
    payload = {
        "summary": args.get("summary") or "Food log",
        "eaten_at": eaten_local.strftime("%Y-%m-%dT%H:%M"),
        "eaten_at_utc": eaten_utc.isoformat(),
        "meal_type": resolve_meal_type(stated, eaten_local),
        "meal_type_source": "stated" if stated else "inferred",
        "items": items,
        "totals": sum_items(items),
        "raw_user_message": ctx.raw_user_message,
    }
    return _add_action(ctx, "create", payload, None, args.get("note"))


def _propose_edit(ctx: ToolContext, args: dict) -> dict:
    tz = ctx.user.timezone
    entry = _entry_or_error(ctx, args["entry_id"])
    items = _parse_items(ctx, args.get("items") or [])
    if args.get("eaten_at"):
        eaten_utc = _parse_local_dt(args["eaten_at"], tz)
    else:
        eaten_utc = entry.eaten_at
    eaten_local = utc_to_local(eaten_utc, tz)
    if args.get("meal_type"):
        meal_type = resolve_meal_type(args["meal_type"], eaten_local)
    elif args.get("eaten_at"):
        meal_type = infer_meal_type(eaten_local)
    else:
        meal_type = entry.meal_type
    payload = {
        "summary": args.get("summary") or f"Edit entry #{entry.id}",
        "entry_id": entry.id,
        "eaten_at": eaten_local.strftime("%Y-%m-%dT%H:%M"),
        "eaten_at_utc": eaten_utc.isoformat(),
        "meal_type": meal_type,
        "items": items,
        "totals": sum_items(items),
        "before": entry_to_dict(entry, tz),
    }
    return _add_action(ctx, "edit", payload, entry.id, args.get("note"))


def _propose_delete(ctx: ToolContext, args: dict) -> dict:
    entry = _entry_or_error(ctx, args["entry_id"])
    payload = {
        "summary": args.get("summary") or f"Delete entry #{entry.id}",
        "entry_id": entry.id,
        "before": entry_to_dict(entry, ctx.user.timezone),
    }
    return _add_action(ctx, "delete", payload, entry.id, args.get("note"))


def _positive_or_none(v, label: str) -> float | None:
    if v is None:
        return None
    if not isinstance(v, (int, float)) or v <= 0:
        raise ToolInputError(f"{label} must be a positive number or null")
    return float(v)


def _propose_recipe(ctx: ToolContext, args: dict) -> dict:
    name = (args.get("name") or "").strip()
    if not name:
        raise ToolInputError("Recipe name is required")
    ingredients = _parse_items(ctx, args.get("ingredients") or [], "ingredients")
    yield_pieces = _positive_or_none(args.get("yield_pieces"), "yield_pieces")
    yield_servings = _positive_or_none(args.get("yield_servings"), "yield_servings")
    cooked_weight_g = _positive_or_none(args.get("cooked_weight_g"), "cooked_weight_g")
    try:
        computed = compute_recipe(ingredients, yield_pieces, yield_servings, cooked_weight_g)
    except FoodError as e:
        raise ToolInputError(str(e)) from e
    existing = find_by_name(ctx.db, ctx.user.id, name, None)
    replaces = existing.id if existing is not None and existing.kind == "recipe" else None
    payload = {
        "summary": f"{'Update' if replaces else 'Save'} recipe: {name}",
        "name": name,
        "replaces_recipe_id": replaces,
        "ingredients": ingredients,
        "yield_pieces": yield_pieces,
        "yield_servings": yield_servings,
        "cooked_weight_g": cooked_weight_g,
        **computed,
    }
    return _add_action(ctx, "save_recipe", payload, None, args.get("note"))


def _propose_water(ctx: ToolContext, args: dict) -> dict:
    amount = args.get("amount_ml")
    if not isinstance(amount, (int, float)) or not 0 < amount <= WATER_MAX_LOG_ML:
        raise ToolInputError(f"amount_ml must be between 1 and {WATER_MAX_LOG_ML}")
    tz = ctx.user.timezone
    drank_utc = _parse_local_dt(args["drank_at"], tz) if args.get("drank_at") else utcnow()
    payload = {
        "summary": f"Water: {amount:g} ml",
        "amount_ml": round(float(amount)),
        "drank_at": utc_to_local(drank_utc, tz).strftime("%Y-%m-%dT%H:%M"),
        "drank_at_utc": drank_utc.isoformat(),
    }
    return _add_action(ctx, "water", payload, None, args.get("note"))


def _get_food(ctx: ToolContext, args: dict) -> dict:
    food = get_user_food(ctx.db, ctx.user.id, args["food_id"])
    if food is None:
        raise ToolInputError(f"No saved food with id {args['food_id']}")
    return food_to_dict(food, with_ingredients=True)


def _get_logs(ctx: ToolContext, args: dict) -> dict:
    start, end = _parse_date(args["start_date"]), _parse_date(args["end_date"])
    if end < start:
        start, end = end, start
    if (end - start).days + 1 > MAX_QUERY_DAYS:
        raise ToolInputError(f"Range too long; max {MAX_QUERY_DAYS} days per call")
    return {"days": logs_by_day(ctx.db, ctx.user, start, end)}


def _get_daily_summary(ctx: ToolContext, args: dict) -> dict:
    return daily_summary(ctx.db, ctx.user, _parse_date(args["date"]))


_HANDLERS = {
    "propose_entry": _propose_entry,
    "propose_edit": _propose_edit,
    "propose_delete": _propose_delete,
    "propose_recipe": _propose_recipe,
    "propose_water": _propose_water,
    "get_food": _get_food,
    "get_logs": _get_logs,
    "get_daily_summary": _get_daily_summary,
}
