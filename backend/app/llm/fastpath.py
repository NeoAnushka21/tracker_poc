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
from app.models import ChatMessage, User
from app.services import general_foods, preferences
from app.services.actions import open_actions
from app.services.foods import FoodError, closest_saved, edit_distance, library_index, normalize_unit, nutrients_for, typo_limit
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


# --- meal-word typos ("brkfst", "bekfast", "lnch", "mornng snak") ----------------------

_MEALS = ("breakfast", "lunch", "dinner", "snack")
_MEAL_SHORTHAND = {"bfast": "breakfast", "b'fast": "breakfast", "brekkie": "breakfast", "brekky": "breakfast",
                   "bkfst": "breakfast"}
# Only a word right after one of these is read as a meal, so "a bunch of grapes" never becomes lunch.
_MEAL_CONTEXT = {"for", "at", "in", "as", "my", "same", "yesterday's", "yesterdays"}
_WORD = re.compile(r"[a-z']+")


def _skeleton(w: str) -> str:
    """Consonants with doubles merged: 'breakfast' and 'brkfst' -> 'brkfst', 'dinner' and 'dinr' -> 'dnr'."""
    return re.sub(r"(.)\1+", r"\1", re.sub(r"[aeiou']", "", w))


def _close_to(word: str, choices: tuple[str, ...]) -> str | None:
    """The one choice `word` is a typo of: letters off (limit by the real word's length),
    vowels dropped ('brkfst'), or the plural ('snacks')."""
    if word in choices:
        return word
    hits = {c for c in choices
            if edit_distance(word, c, typo_limit(c)) <= typo_limit(c)
            or (len(word) >= 4 and _skeleton(word) == _skeleton(c))}
    return hits.pop() if len(hits) == 1 else None


def _fix_meal_typos(text: str) -> str:
    """Spell misspelt meal words the standard way, so the rules below recognise them."""
    words = text.split(" ")
    for i in range(1, len(words)):
        if _WORD.sub("", words[i - 1]) or words[i - 1] not in _MEAL_CONTEXT:
            continue
        m = _WORD.match(words[i])
        if not m:
            continue
        w, rest = m.group(), words[i][m.end():]
        nxt = _WORD.match(words[i + 1]) if i + 1 < len(words) else None
        part = _close_to(w, ("morning", "evening"))
        if part and nxt and _close_to(nxt.group(), ("snack",)):
            words[i], words[i + 1] = part, "snack" + words[i + 1][nxt.end():]
            continue
        meal = _MEAL_SHORTHAND.get(w) or _close_to(w, _MEALS)
        if meal:
            words[i] = meal + rest
    return " ".join(words)


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
_MACRO_WORDS = r"protein|calories|calorie|kcal|carbs|carb|carbohydrates|fat|fats|fiber|fibre"
_TODAY = r"(?: (?:today|so far|so far today|today so far))?"
_SUMMARY = re.compile(
    r"(?:(?:what'?s|what is|whats) (?:left|remaining)(?: for today| today)?"
    r"|how much (?P<macro>" + _MACRO_WORDS + r")? ?"
    r"(?:do i have |is |have i got )?(?:left|remaining)(?: for today| today)?"
    # "how much protein did I eat today?", "how many calories have I had so far?" (today only:
    # any other day word fails the full match and goes to the model)
    r"|how (?:much|many) (?P<eaten>" + _MACRO_WORDS + r")? ?(?:did i|have i|i have|i've) "
    r"(?:eat|eaten|ate|have|had|get|got|consume|consumed|take|taken)" + _TODAY +
    r"|(?:what'?s|what is|whats) my (?P<mine>" + _MACRO_WORDS + r")(?: intake| count| total)?" + _TODAY +
    r"|(?:my )?(?P<total>" + _MACRO_WORDS + r") (?:intake |count |total )?(?:today|so far)"
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
    macro = _MACROS.get(m.group("macro") or m.group("eaten") or m.group("mine") or m.group("total") or "")

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


# --- 4. foods from My Foods or the general food list ---------------------------------------

_MEAL_WORDS = {"breakfast": "breakfast", "lunch": "lunch", "dinner": "dinner", "morning snack": "morning_snack",
               "evening snack": "evening_snack", "snack": "snack"}
_MEAL_RE = re.compile(r"\s*\b(?:for|at|in|as)?\s*(?:my\s+)?(morning snack|evening snack|breakfast|lunch|dinner|snack)\b\s*")
_FILLER = re.compile(r"^(?:i\s+)?(?:just\s+)?(?:have\s+)?(?:had|ate|eaten|have|log|add)\s+")
# Mentions of time, other days, drinks with water, or brands send the message to the model.
_NOT_SIMPLE = re.compile(r"\b(?:yesterday|tomorrow|morning|afternoon|evening|night|ago|am|pm|at \d|water|"
                         r"instead|recipe|not|without|extra|less|more)\b|\d:\d")
_ITEM = re.compile(_NUM + r"?\s*(?P<unit>g|gm|gms|grams?|kg|ml|l|pcs?|pieces?|servings?|slices?|nos?|"
                   r"tbsps?|tsps?|tablespoons?|teaspoons?|cups?)?\s*(?:of\s+)?(?P<name>[a-z][a-z \-']*)")
_SPLIT = re.compile(r"\s*(?:,|\band\b|&|\+|\bplus\b)\s*")
_ASK = "ask"   # _resolve_item: the raw/cooked state must be asked first


def _saved_match(index: dict, typed: str, state: str | None):
    """(saved food, spelt exactly?) for a typed name; with a state, 'cooked chicken breast' also
    finds 'chicken breast, cooked'."""
    names = [typed]
    if state:
        rest = general_foods.strip_state(typed)
        names += [n for w, s in general_foods.STATE_WORDS.items() if s == state for n in (f"{rest} {w}", f"{w} {rest}")]
    for name in names:
        food = closest_saved(index, name)
        if food is not None:
            return food, name in index
    return None, False


def _resolve_item(index: dict, typed: str, qty: float, unit: str | None) -> tuple[dict, str | None] | str | None:
    """(card item, what a typo was read as) from My Foods, else from the general list;
    _ASK when the user must say raw or cooked; None to leave the message to the model."""
    state = general_foods.state_in(typed)
    food, exact = _saved_match(index, typed, state)
    if food is not None:
        saved_state = general_foods.state_in(food.name)
        if saved_state and not state and unit is not None:
            return _ASK                                  # saved as "chicken breast, cooked", typed "chicken breast"
        if saved_state and state and saved_state != state:
            food = None                                  # typed raw, saved cooked: not the same food
    if food is not None:
        u = unit or ("piece" if (food.grams_per_piece or normalize_unit(food.ref_unit)[0] == "piece")
                     else "serving" if (food.grams_per_serving or normalize_unit(food.ref_unit)[0] == "serving")
                     else None)
        try:
            if u is None:
                raise FoodError("no unit")
            nutrients_for(food, qty, u)
            return ({"ingredient_name": food.name, "brand_name": None, "quantity": qty, "unit": u,
                     "calories": 0, "protein_g": 0, "carbs_g": 0, "fat_g": 0, "fiber_g": 0,
                     "food_id": food.id, "general_id": None, "unit_weight_g": None, "micronutrients": None},
                    None if exact else f"'{typed}' as {food.name}")
        except FoodError:
            pass                                         # e.g. "1 cup" of a food saved per 100 g: try the list
    m = general_foods.find(typed)
    if m is None:
        return None
    if m.entry is None:
        # Counted pieces ("2 drumsticks") have no raw/cooked question; the model handles those.
        return _ASK if unit is not None else None
    u = unit or ("piece" if m.entry["grams_per_piece"] else None)
    if u is None or general_foods.grams_for(m.entry, qty, u) is None:
        return None
    return ({"ingredient_name": general_foods.display_name(m.entry), "brand_name": None, "quantity": qty, "unit": u,
             "calories": 0, "protein_g": 0, "carbs_g": 0, "fat_g": 0, "fiber_g": 0, "food_id": None,
             "general_id": m.entry["id"], "unit_weight_g": None, "micronutrients": None}, None)


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
    index = library_index(ctx.db, ctx.user.id)
    items, read_as, ask = [], [], []
    for part in _SPLIT.split(body):
        part = part.strip()
        if not part:
            continue
        m = _ITEM.fullmatch(part)
        if not m or not m.group("num"):
            return None
        typed = re.sub(r"\s+", " ", m.group("name")).strip()
        got = _resolve_item(index, typed, _num(m.group("num")), m.group("unit"))
        if got is None:
            return None
        if got == _ASK:
            ask.append(typed)
            continue
        item, read = got
        items.append(item)
        if read:
            read_as.append(read)
    if ask:
        # Raw and cooked differ by 25-80% per 100 g: ask, never assume (owner's rule, 2026-09-30).
        ctx.reply_data = {"ask_state": {"text": text, "items": ask}}
        if len(ask) == 1:
            return (f"Was the {ask[0]} weighed raw or cooked? The calories per 100 g are very different, "
                    "so I'd rather ask than guess.")
        return (f"Were these weighed raw or cooked: {', '.join(ask)}? Reply with one word for all, "
                f"or e.g. '{ask[0]} raw, {ask[1]} cooked'.")
    if not items:
        return None
    meal = next(iter(meals), None)
    names = ", ".join(f"{i['quantity']:g} {i['ingredient_name']}" for i in items)
    general = [i["ingredient_name"] for i in items if i["general_id"]]
    if not general:
        source = "All from your saved foods, so the numbers match last time."
    elif len(general) == len(items):
        source = f"From the general food list ({general_foods.SOURCE_NOTE}), plain food with no oil or salt."
    else:
        source = f"From your saved foods and the general food list ({', '.join(general)})."
    try:
        run_tool(ctx, "propose_entry", {
            "summary": names[:80], "meal_type": meal, "eaten_at": None, "items": items,
            "note": (f"I read {', '.join(read_as)}. " if read_as else "") + source + " Confirm if it looks right."
                    + (f" {h}" if (h := preferences.allergen_note(ctx.user, [i["ingredient_name"] for i in items]))
                       else ""),
        })
    except ToolInputError:
        return None
    return ctx.notes[-1]


# --- 4b. the answer to "raw or cooked?" ----------------------------------------------------

_ANSWER_SPLIT = re.compile(r"\s*(?:,|;|\band\b|&)\s*")


def _state_answer(ctx: ToolContext, text: str) -> str | None:
    """'cooked' (or 'chicken raw, rice cooked') right after the raw/cooked question: log it."""
    last = (ctx.db.query(ChatMessage).filter(ChatMessage.user_id == ctx.user.id, ChatMessage.role == "assistant")
            .order_by(ChatMessage.id.desc()).first())
    ask = ((last.data or {}) if last else {}).get("ask_state")
    if not ask or len(text) > 80:
        return None
    # Typos in the answer: "cookd" -> cooked, "uncookd" -> uncooked.
    text = " ".join(_close_to(w, tuple(general_foods.STATE_WORDS)) or w for w in text.split(" "))
    states: dict[str, str] = {}
    for seg in _ANSWER_SPLIT.split(text):
        st, rest = general_foods.state_in(seg), general_foods.strip_state(seg)
        for it in ask["items"]:
            if st and rest and (rest in it or it in rest or _close_to(rest, (it,))):
                states[it] = st
    every = general_foods.state_in(text)
    for it in ask["items"]:
        if states.setdefault(it, every) is None:
            return None
    rebuilt = ask["text"]
    for it in ask["items"]:
        rebuilt = re.sub(rf"\b{re.escape(it)}\b", f"{states[it]} {it}", rebuilt, count=1)
    return _library_log(ctx, rebuilt)


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


HANDLERS = [("state_answer", _state_answer), ("water", _water), ("confirm_nudge", _yes), ("summary", _summary),
            ("repeat_meal", _same_as_yesterday), ("library_log", _library_log)]


def try_fastpath(db: Session, user: User, text: str, ctx: ToolContext) -> tuple[str, str] | None:
    """(handler name, reply text) if a rule handled the message, else None."""
    cleaned = _fix_meal_typos(_clean(text))
    if not cleaned or len(cleaned) > 200:
        return None
    for name, handler in HANDLERS:
        reply = handler(ctx, cleaned)
        if reply:
            return name, reply
    return None


assert set(v for v in _MEAL_WORDS.values() if v != "snack") <= set(MEAL_TYPES)
