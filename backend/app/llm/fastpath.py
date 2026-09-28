"""L0: common messages answered by rules, with no model call.

Each handler either returns the reply text (having created any proposal cards through the
same tool handlers the model uses, so cards look and behave identically) or None to let the
message go to the model. They are deliberately strict: when unsure, fall through. A missed
fast path only costs a model call; a wrong card is still caught by the Confirm step.
"""
import re
from datetime import timedelta

from sqlalchemy.orm import Session

from app.config import MEAL_TYPES
from app.llm.tools import ToolContext, ToolInputError, run_tool
from app.models import User
from app.services.actions import open_actions
from app.services.foods import FoodError, list_foods, normalize_unit, nutrients_for
from app.services.logs import daily_summary, entries_between
from app.timeutil import local_today

_NUM_WORDS = {"a": 1, "an": 1, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6,
              "seven": 7, "eight": 8, "nine": 9, "ten": 10, "half": 0.5, "half a": 0.5, "half an": 0.5}
_NUM = r"(?P<num>\d+(?:\.\d+)?|half an?|an?|one|two|three|four|five|six|seven|eight|nine|ten|half)"


def _num(s: str) -> float:
    s = s.lower().strip()
    return float(s) if re.fullmatch(r"\d+(?:\.\d+)?", s) else _NUM_WORDS[s]


def _clean(text: str) -> str:
    t = text.strip().lower()
    t = re.sub(r"[.!]+$", "", t).strip()
    return re.sub(r"\s+", " ", t)


# --- 1. water ------------------------------------------------------------------

_WATER = re.compile(
    r"(?:i\s+)?(?:just\s+)?(?:drank|had|drink|log|add|finished)?\s*" + _NUM +
    r"\s*(?P<unit>ml|millilitres?|milliliters?|l|litres?|liters?|ltrs?|glass(?:es)?|cups?|bottles?)"
    r"\s*(?:of\s+)?(?:plain\s+|normal\s+|drinking\s+)?water(?:\s+(?:just now|now))?")
_WATER_ML = {"glass": 250, "cup": 250, "bottle": 500}


def _water(ctx: ToolContext, text: str) -> str | None:
    m = _WATER.fullmatch(text)
    if not m:
        return None
    n, unit = _num(m.group("num")), m.group("unit")
    if unit.startswith(("glass", "cup", "bottle")):
        ml = n * next(v for k, v in _WATER_ML.items() if unit.startswith(k))
    elif unit == "ml" or unit.startswith("milli"):
        ml = n
    else:   # l, ltr, litre, liter
        ml = n * 1000
    try:
        run_tool(ctx, "propose_water", {"amount_ml": ml, "note": f"{ml:g} ml of water, nice. Confirm and it's on the tracker."})
    except ToolInputError:
        return None
    return ctx.notes[-1]


# --- 2. "yes" while a card is waiting -----------------------------------------------

_YES = re.compile(r"(?:yes|yep|yeah|yup|ya|ok|okay|k|sure|looks good|lgtm|correct|confirm(?:ed)?|"
                  r"done|perfect|great|save it|go ahead|👍)(?:\s+(?:bro|thanks|thank you))?")


def _yes(ctx: ToolContext, text: str) -> str | None:
    if not _YES.fullmatch(text) or not open_actions(ctx.db, ctx.user.id):
        return None
    return ("Tap **Looks good** on the card to save it (or **Needs changes** to tweak it). "
            "I can't save anything from a chat message; the button makes sure you've checked it.")


# --- 3. today's summary / what's left ----------------------------------------------

_MACROS = {"protein": "protein_g", "calories": "calories", "calorie": "calories", "kcal": "calories",
           "carbs": "carbs_g", "carb": "carbs_g", "carbohydrates": "carbs_g", "fat": "fat_g", "fats": "fat_g",
           "fiber": "fiber_g", "fibre": "fiber_g"}
_SUMMARY = re.compile(
    r"(?:(?:what'?s|what is|whats) (?:left|remaining)(?: for today| today)?"
    r"|how much (?P<macro>protein|calories|calorie|kcal|carbs|carb|carbohydrates|fat|fats|fiber|fibre)? ?"
    r"(?:do i have |is |have i got )?(?:left|remaining)(?: for today| today)?"
    r"|(?:today'?s |my )?(?:summary|progress|status)(?: for today| today| so far)?"
    r"|how am i doing(?: today)?|day so far)\??")


def _summary(ctx: ToolContext, text: str) -> str | None:
    m = _SUMMARY.fullmatch(text)
    if not m:
        return None
    s = daily_summary(ctx.db, ctx.user, local_today(ctx.user.timezone))
    t, c = s.get("targets"), s["consumed"]
    if not t:
        return None
    macro = _MACROS.get(m.group("macro") or "")

    def line(label: str, key: str, unit: str) -> str:
        left = t[key] - c[key]
        status = f"{abs(round(left)):,} {unit} {'left' if left >= 0 else 'over'}"
        if key == "fiber_g" and left <= 0:
            status = "goal met"
        return f"{label}: {round(c[key]):,} / {round(t[key]):,} {unit} ({status})"

    kcal = line("Calories", "calories", "kcal")
    if macro and macro != "calories":
        label = {"protein_g": "Protein", "carbs_g": "Carbs", "fat_g": "Fat", "fiber_g": "Fiber"}[macro]
        return f"{line(label, macro, 'g')}\n{kcal}"
    lines = [f"Here's today so far:", f"- {kcal}"] + [
        f"- {line(lbl, key, 'g')}" for lbl, key in
        (("Protein", "protein_g"), ("Carbs", "carbs_g"), ("Fat", "fat_g"), ("Fiber", "fiber_g"))
    ]
    w = s.get("water")
    if w and w.get("target_ml"):
        lines.append(f"- Water: {w['consumed_ml'] / 1000:.1f} / {w['target_ml'] / 1000:.1f} L")
    return "\n".join(lines)


# --- 4. foods that are all in My foods ---------------------------------------------

_MEAL_WORDS = {"breakfast": "breakfast", "lunch": "lunch", "dinner": "dinner", "morning snack": "morning_snack",
               "evening snack": "evening_snack", "snack": "snack"}
_MEAL_RE = re.compile(r"\s*\b(?:for|at|in|as)?\s*(?:my\s+)?(morning snack|evening snack|breakfast|lunch|dinner|snack)\b\s*")
_FILLER = re.compile(r"^(?:i\s+)?(?:just\s+)?(?:have\s+)?(?:had|ate|eaten|have|log|add)\s+")
# Mentions of time, other days, drinks with water, or brands send the message to the model.
_NOT_SIMPLE = re.compile(r"\b(?:yesterday|tomorrow|morning|afternoon|evening|night|ago|am|pm|at \d|water|"
                         r"instead|recipe|not|without|extra|less|more)\b|\d:\d")
_ITEM = re.compile(_NUM + r"?\s*(?P<unit>g|gm|gms|grams?|kg|ml|l|pcs?|pieces?|servings?|slices?|nos?)?\s*(?:of\s+)?(?P<name>[a-z][a-z \-']*)")
_SPLIT = re.compile(r"\s*(?:,|\band\b|&|\+|\bplus\b)\s*")


def _variants(name: str) -> set[str]:
    n = re.sub(r"[^a-z0-9 ]", " ", name.lower())
    n = re.sub(r"\s+", " ", n).strip()
    out = {n}
    out |= {n + "s", n + "es"}
    if n.endswith("es"):
        out.add(n[:-2])
    if n.endswith("s"):
        out.add(n[:-1])
    return out


def _library_index(ctx: ToolContext) -> dict[str, object]:
    foods = list_foods(ctx.db, ctx.user.id)
    index: dict[str, object] = {}
    ambiguous: set[str] = set()
    for f in foods:
        keys = _variants(f.name)
        if "," in f.name:   # "eggs, large" can be called "eggs" if nothing else is
            keys |= _variants(f.name.split(",")[0])
        for k in keys:
            if k in index and index[k] is not f:
                ambiguous.add(k)
            index[k] = f
    for k in ambiguous:
        index.pop(k, None)
    return index


def _library_log(ctx: ToolContext, text: str) -> str | None:
    meals = {_MEAL_WORDS[m] for m in _MEAL_RE.findall(text)}
    if len(meals) > 1:
        return None
    without_meal = _MEAL_RE.sub(" ", text)
    if _NOT_SIMPLE.search(without_meal):
        return None
    body = _FILLER.sub("", without_meal.strip()).strip(" ,")
    if not body:
        return None
    index = _library_index(ctx)
    items = []
    for part in _SPLIT.split(body):
        part = part.strip()
        if not part:
            continue
        m = _ITEM.fullmatch(part)
        if not m or not m.group("num"):
            return None
        food = index.get(re.sub(r"\s+", " ", m.group("name")).strip())
        if food is None:
            return None
        qty = _num(m.group("num"))
        unit = m.group("unit")
        if unit is None:
            # No unit: count of pieces (or servings), only if the food has such a measure.
            unit = ("piece" if (food.grams_per_piece or normalize_unit(food.ref_unit)[0] == "piece")
                    else "serving" if (food.grams_per_serving or normalize_unit(food.ref_unit)[0] == "serving")
                    else None)
            if unit is None:
                return None
        try:
            nutrients_for(food, qty, unit)
        except FoodError:
            return None
        items.append({"ingredient_name": food.name, "brand_name": None, "quantity": qty, "unit": unit,
                      "calories": 0, "protein_g": 0, "carbs_g": 0, "fat_g": 0, "fiber_g": 0,
                      "food_id": food.id, "unit_weight_g": None, "micronutrients": None})
    if not items:
        return None
    meal = next(iter(meals), None)
    names = ", ".join(f"{i['quantity']:g} {i['ingredient_name']}" for i in items)
    try:
        run_tool(ctx, "propose_entry", {
            "summary": names[:80], "meal_type": meal, "eaten_at": None, "items": items,
            "note": "All from your saved foods, so the numbers match last time. Confirm if it looks right.",
        })
    except ToolInputError:
        return None
    return ctx.notes[-1]


# --- 5. same meal as yesterday ------------------------------------------------------

_SAME = re.compile(
    r"(?:(?:same|repeat|copy)(?: my)? (?P<m1>breakfast|lunch|dinner|morning snack|evening snack) "
    r"(?:as|from) yesterday(?:'s)?"
    r"|(?:same|repeat|copy)(?: as)? yesterday'?s (?P<m2>breakfast|lunch|dinner|morning snack|evening snack))"
    r"(?: again| today| for today)?")


def _same_as_yesterday(ctx: ToolContext, text: str) -> str | None:
    m = _SAME.fullmatch(text)
    if not m:
        return None
    meal = _MEAL_WORDS[m.group("m1") or m.group("m2")]
    today = local_today(ctx.user.timezone)
    yesterday = today - timedelta(days=1)
    entries = [e for e in entries_between(ctx.db, ctx.user, yesterday, yesterday) if e.meal_type == meal]
    label = meal.replace("_", " ")
    if not entries:
        return f"I don't see a {label} logged yesterday, so there's nothing to copy. Tell me what you had?"
    try:
        for e in entries:
            run_tool(ctx, "propose_move", {
                "entry_id": e.id, "item_ids": None, "to_meal_type": meal, "to_date": today.isoformat(),
                "mode": "copy", "summary": f"Yesterday's {label}, again",
                "note": f"Same {label} as yesterday. Confirm to add it to today.",
            })
    except ToolInputError:
        return None
    return ctx.notes[-1]


HANDLERS = [("water", _water), ("confirm_nudge", _yes), ("summary", _summary),
            ("repeat_meal", _same_as_yesterday), ("library_log", _library_log)]


def try_fastpath(db: Session, user: User, text: str, ctx: ToolContext) -> tuple[str, str] | None:
    """(handler name, reply text) if a rule handled the message, else None."""
    cleaned = _clean(text)
    if not cleaned or len(cleaned) > 200:
        return None
    for name, handler in HANDLERS:
        reply = handler(ctx, cleaned)
        if reply:
            return name, reply
    return None


assert set(v for v in _MEAL_WORDS.values() if v != "snack") <= set(MEAL_TYPES)
