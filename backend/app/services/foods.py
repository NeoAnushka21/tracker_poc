"""Personal food library and recipes.

Every food stores nutrients for a reference amount (e.g. 100 g, 1 piece, 1 serving),
plus optional gram weights per piece/serving. `nutrients_for` scales in code, so for
known foods the LLM only has to recognise the food; it never does the maths.
"""
import re

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models import RecipeIngredient, User, UserFood, utcnow
from app.services import micros

NUTRIENTS = ("calories", "protein_g", "carbs_g", "fat_g", "fiber_g")
MASS_UNITS = ("g", "ml")          # treated as interchangeable (density ~1; fine for most foods)
CONTEXT_FOOD_LIMIT = 150          # library entries listed to the LLM each turn

_UNIT_ALIASES = {
    "g": ("g", 1), "gm": ("g", 1), "gms": ("g", 1), "gram": ("g", 1), "grams": ("g", 1), "gr": ("g", 1),
    "kg": ("g", 1000), "kgs": ("g", 1000), "kilogram": ("g", 1000), "kilograms": ("g", 1000),
    "ml": ("ml", 1), "millilitre": ("ml", 1), "milliliter": ("ml", 1), "millilitres": ("ml", 1), "milliliters": ("ml", 1),
    "l": ("ml", 1000), "litre": ("ml", 1000), "liter": ("ml", 1000), "litres": ("ml", 1000), "liters": ("ml", 1000),
    "piece": ("piece", 1), "pieces": ("piece", 1), "pc": ("piece", 1), "pcs": ("piece", 1), "no": ("piece", 1),
    "nos": ("piece", 1), "whole": ("piece", 1), "count": ("piece", 1), "item": ("piece", 1), "items": ("piece", 1),
    "serving": ("serving", 1), "servings": ("serving", 1), "portion": ("serving", 1), "portions": ("serving", 1),
}


class FoodError(Exception):
    """A problem the LLM (or user) can fix, e.g. a unit that can't be converted."""


def normalize_unit(unit: str) -> tuple[str, float]:
    """'kg' -> ('g', 1000); 'Cups' -> ('cup', 1); unknown units are kept, lower-cased and singular."""
    u = unit.strip().lower().rstrip(".")
    if u in _UNIT_ALIASES:
        return _UNIT_ALIASES[u]
    if len(u) > 3 and u.endswith("es") and u[:-2] in ("glass", "dish", "pouch"):
        return u[:-2], 1
    if len(u) > 2 and u.endswith("s"):
        return u[:-1], 1
    return u, 1


def name_key(name: str, brand: str | None = None) -> str:
    text = f"{name} {brand or ''}".lower()
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return " ".join(text.split())


def _grams(food: UserFood, qty: float, unit: str) -> float | None:
    if unit in MASS_UNITS:
        return qty
    if unit == "piece" and food.grams_per_piece:
        return qty * food.grams_per_piece
    if unit == "serving" and food.grams_per_serving:
        return qty * food.grams_per_serving
    return None


def scale_factor(food: UserFood, qty: float, unit: str) -> float:
    """How many reference amounts `qty unit` of this food is."""
    u, mult = normalize_unit(unit)
    qty = qty * mult
    ref_u, _ = normalize_unit(food.ref_unit)
    if u == ref_u or (u in MASS_UNITS and ref_u in MASS_UNITS):
        return qty / food.ref_qty
    grams = _grams(food, qty, u)
    ref_grams = _grams(food, food.ref_qty, ref_u)
    if grams is not None and ref_grams:
        return grams / ref_grams
    raise FoodError(
        f"Can't convert '{unit}' for '{food.name}'. It can be measured in: "
        f"{', '.join(measurable_units(food))}. Ask the user for one of those, or estimate in grams."
    )


def measurable_units(food: UserFood) -> list[str]:
    """Units this food can be logged in: its reference unit, grams when its weight is known,
    and pieces/servings when their gram weights are saved."""
    ref_u, _ = normalize_unit(food.ref_unit)
    units = [ref_u]
    if _grams(food, food.ref_qty, ref_u):
        units.append("g")
    if food.grams_per_piece:
        units.append("piece")
    if food.grams_per_serving:
        units.append("serving")
    return list(dict.fromkeys(units))


def nutrients_for(food: UserFood, qty: float, unit: str) -> dict:
    f = scale_factor(food, qty, unit)
    return {
        **{k: round((getattr(food, k) or 0) * f, 1) for k in NUTRIENTS},
        "micronutrients": micros.scale(food.micronutrients, f),
    }


def reference_for(qty: float, unit: str, nutrients: dict) -> tuple[float, str, dict]:
    """An amount + its nutrients -> stored reference: per 100 g/ml, else per 1 unit."""
    u, mult = normalize_unit(unit)
    qty = qty * mult
    ref_qty = 100.0 if u in MASS_UNITS else 1.0
    f = ref_qty / qty
    return ref_qty, u, {k: round((nutrients.get(k) or 0) * f, 2) for k in NUTRIENTS}


# --- queries ------------------------------------------------------------------

def get_user_food(db: Session, user_id: int, food_id: int) -> UserFood | None:
    food = db.get(UserFood, food_id)
    return food if food is not None and food.user_id == user_id else None


def find_by_name(db: Session, user_id: int, name: str, brand: str | None) -> UserFood | None:
    stmt = select(UserFood).where(UserFood.user_id == user_id, UserFood.name_key == name_key(name, brand))
    return db.scalars(stmt).first()


def list_foods(db: Session, user_id: int, limit: int | None = None) -> list[UserFood]:
    stmt = (
        select(UserFood).where(UserFood.user_id == user_id)
        .options(selectinload(UserFood.ingredients).selectinload(RecipeIngredient.food))
        .order_by(UserFood.last_used_at.desc(), UserFood.id.desc())
    )
    if limit:
        stmt = stmt.limit(limit)
    return list(db.scalars(stmt))


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


def library_index(db: Session, user_id: int) -> dict[str, UserFood]:
    """Lower-case name (and plural/singular variants) -> saved food. Names that could mean
    two different foods are left out, so a lookup never picks the wrong one."""
    index: dict[str, UserFood] = {}
    ambiguous: set[str] = set()
    for f in list_foods(db, user_id):
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


def _key(name: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9 ]", " ", name.lower())).strip()


def match_saved(db: Session, user_id: int, name: str) -> UserFood | None:
    """The saved food a typed name clearly refers to, else None."""
    return library_index(db, user_id).get(_key(name))


# --- typos: plain Python, no AI ------------------------------------------------------

def typo_limit(word: str) -> int:
    """How many letters may be wrong: none for short words ('egg' vs 'fig' are different
    foods), one from 5 letters, two from 9."""
    n = len(word)
    return 0 if n < 5 else 1 if n < 9 else 2


def edit_distance(a: str, b: str, limit: int) -> int:
    """Letters added, dropped, changed or swapped ('panere' -> 'paneer' is 1) to turn a into b.
    Stops early and returns limit + 1 once the distance is sure to exceed `limit`."""
    if abs(len(a) - len(b)) > limit:
        return limit + 1
    prev2, prev = None, list(range(len(b) + 1))
    for i in range(1, len(a) + 1):
        cur = [i] + [0] * len(b)
        for j in range(1, len(b) + 1):
            cur[j] = min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (a[i - 1] != b[j - 1]))
            if i > 1 and j > 1 and a[i - 1] == b[j - 2] and a[i - 2] == b[j - 1]:
                cur[j] = min(cur[j], prev2[j - 2] + 1)   # swapped neighbours
        if min(cur) > limit:
            return limit + 1
        prev2, prev = prev, cur
    return prev[-1]


def closest_saved(index: dict, name: str, strict: bool = False):
    """The food a misspelt name means ('panner' -> Paneer), else None. Only when exactly one
    food is that close, so a typo never picks between two foods. `strict` is for the big
    general list: typos only from 6 letters, and the first letter must be right ('idlis' is
    not 'imlis')."""
    key = _key(name)
    if key in index:
        return index[key]
    limit = typo_limit(key[1:]) if strict else typo_limit(key)
    if not limit:
        return None
    close = {id(f): f for k, f in index.items()
             if (not strict or k[:1] == key[:1]) and edit_distance(key, k, limit) <= limit}
    return next(iter(close.values())) if len(close) == 1 else None


def recipes_using(db: Session, food_id: int) -> list[UserFood]:
    # A subquery instead of JOIN + DISTINCT: Postgres can't compare JSON columns for DISTINCT.
    stmt = select(UserFood).where(UserFood.id.in_(
        select(RecipeIngredient.recipe_id).where(RecipeIngredient.food_id == food_id)))
    return list(db.scalars(stmt))


def _measures(food: UserFood) -> str:
    ref = f"per {food.ref_qty:g} {food.ref_unit}"
    extra = []
    if food.grams_per_piece:
        extra.append(f"1 piece = {food.grams_per_piece:g} g")
    if food.grams_per_serving:
        extra.append(f"1 serving = {food.grams_per_serving:g} g")
    return ref + (f" ({'; '.join(extra)})" if extra else "")


def food_to_dict(food: UserFood, with_ingredients: bool = False) -> dict:
    d = {
        "id": food.id,
        "name": food.name,
        "brand_name": food.brand_name,
        "kind": food.kind,
        "source": food.source,
        "ref_qty": food.ref_qty,
        "ref_unit": food.ref_unit,
        **{k: round(getattr(food, k) or 0, 1) for k in NUTRIENTS},
        "grams_per_piece": food.grams_per_piece,
        "grams_per_serving": food.grams_per_serving,
        "yield_pieces": food.yield_pieces,
        "yield_servings": food.yield_servings,
        "cooked_weight_g": food.cooked_weight_g,
        "measures": _measures(food),
        "units": measurable_units(food),
        "micronutrients": food.micronutrients,
        "last_used_at": food.last_used_at.isoformat() + "Z",
    }
    if with_ingredients and food.kind == "recipe":
        d["ingredients"] = [
            {"food_id": ri.food_id, "name": ri.food.name, "quantity": ri.quantity, "unit": ri.unit,
             **nutrients_for_safe(ri.food, ri.quantity, ri.unit)}
            for ri in food.ingredients
        ]
    return d


def nutrients_for_safe(food: UserFood, qty: float, unit: str) -> dict:
    try:
        return nutrients_for(food, qty, unit)
    except FoodError:
        return {**{k: None for k in NUTRIENTS}, "micronutrients": None}


def _stems(text: str) -> set[str]:
    """Lowercase word stems (plural 's'/'es' dropped), 3+ letters, for loose name matching."""
    words = re.findall(r"[a-z]{3,}", text.lower())
    return {re.sub(r"(?:es|s)$", "", w) or w for w in words} - _STOPWORDS


_STOPWORDS = {"had", "ate", "the", "and", "for", "with", "some", "cup", "glass", "piece", "cooked", "raw",
              "breakfast", "lunch", "dinner", "snack", "morning", "evening", "today", "yesterday"}


def _shares_word(food_words: set[str], wanted: set[str]) -> bool:
    if food_words & wanted:
        return True
    return any(edit_distance(w, s, lim) <= lim for s in food_words for w in wanted
               if (lim := min(typo_limit(w), typo_limit(s))))


def library_context(db: Session, user: User, match_text: str | None = None) -> list[str]:
    """Compact lines listing the user's foods for the LLM: 'id | name | kind | measures'.
    With match_text, only foods sharing a word with it (allowing a typo, see typo_limit) are
    listed (a big token saving)."""
    foods = list_foods(db, user.id, CONTEXT_FOOD_LIMIT)
    if match_text is not None:
        wanted = _stems(match_text)
        foods = [f for f in foods if _shares_word(_stems(f"{f.name} {f.brand_name or ''}"), wanted)]
    return [
        f"{f.id} | {f.name}{f' ({f.brand_name})' if f.brand_name else ''}"
        f"{' | RECIPE' if f.kind == 'recipe' else ''} | {_measures(f)}"
        for f in foods
    ]


# --- resolving proposed items -----------------------------------------------------

def resolve_library_item(db: Session, user: User, item: dict) -> dict:
    """Fill a proposed item's nutrients from the library entry it references."""
    food = get_user_food(db, user.id, item["food_id"])
    if food is None:
        raise FoodError(f"food_id {item['food_id']} isn't in the user's library. Use null and estimate instead.")
    return {
        **item,
        "ingredient_name": food.name,
        "brand_name": food.brand_name,
        **nutrients_for(food, item["quantity"], item["unit"]),
        "source": "recipe" if food.kind == "recipe" else "library",
    }


def compute_recipe(ingredients: list[dict], yield_pieces: float | None,
                   yield_servings: float | None, cooked_weight_g: float | None) -> dict:
    """Whole-batch totals -> the recipe's stored reference amount and nutrients."""
    total = {k: sum(i[k] for i in ingredients) for k in NUTRIENTS}
    total_micros = micros.total(i.get("micronutrients") for i in ingredients)
    if yield_pieces:
        ref_qty, ref_unit, divisor = 1.0, "piece", yield_pieces
    elif cooked_weight_g:
        ref_qty, ref_unit, divisor = 100.0, "g", cooked_weight_g / 100
    elif yield_servings:
        ref_qty, ref_unit, divisor = 1.0, "serving", yield_servings
    else:
        raise FoodError(
            "A recipe needs a yield: how many pieces it makes, how many servings, or the "
            "cooked weight of the whole batch. Ask the user."
        )
    per_ref = {k: round(v / divisor, 2) for k, v in total.items()}
    return {
        "ref_qty": ref_qty,
        "ref_unit": ref_unit,
        "per_ref": per_ref,
        "per_ref_micronutrients": micros.scale(total_micros, 1 / divisor),
        "batch_totals": {k: round(v, 1) for k, v in total.items()},
        "grams_per_piece": round(cooked_weight_g / yield_pieces, 1) if yield_pieces and cooked_weight_g else None,
        "grams_per_serving": round(cooked_weight_g / yield_servings, 1) if yield_servings and cooked_weight_g else None,
    }


# --- writes (only ever called from a confirmed action or a direct user edit) ------

def upsert_estimate(db: Session, user: User, item: dict) -> UserFood | None:
    """Save a confirmed LLM estimate to the library. The latest confirmed values win,
    except that an estimate never overwrites a recipe or a hand-edited food."""
    if item.get("quantity", 0) <= 0:
        return None
    existing = find_by_name(db, user.id, item["ingredient_name"], item.get("brand_name"))
    if existing is not None and existing.source in ("recipe", "user"):
        existing.last_used_at = utcnow()
        return existing

    ref_qty, ref_unit, per_ref = reference_for(item["quantity"], item["unit"], item)
    food = existing or UserFood(
        user_id=user.id,
        name=item["ingredient_name"],
        name_key=name_key(item["ingredient_name"], item.get("brand_name")),
        brand_name=item.get("brand_name"),
    )
    food.kind, food.source = "food", "estimate"
    food.ref_qty, food.ref_unit = ref_qty, ref_unit
    for k in NUTRIENTS:
        setattr(food, k, per_ref[k])
    food.micronutrients = micros.scale(item.get("micronutrients"), ref_qty / (item["quantity"] * normalize_unit(item["unit"])[1]))
    weight = item.get("unit_weight_g")
    if weight and ref_unit == "piece":
        food.grams_per_piece = weight
    elif weight and ref_unit == "serving":
        food.grams_per_serving = weight
    food.last_used_at = utcnow()
    if existing is None:
        db.add(food)
    db.flush()
    return food


def upsert_general(db: Session, user: User, item: dict) -> UserFood | None:
    """Save a confirmed general-list food to the library with the list's exact numbers per
    100 g (and piece weight). An existing saved food of that name is kept as it is."""
    from app.services import general_foods
    entry = general_foods.get(item["general_id"])
    if entry is None:
        return upsert_estimate(db, user, item)
    name = general_foods.display_name(entry)
    food = find_by_name(db, user.id, name, None)
    if food is None:
        food = UserFood(user_id=user.id, name=name, name_key=name_key(name, None), brand_name=None,
                        kind="food", source="general", ref_qty=100.0, ref_unit="g",
                        **{k: entry[k] for k in NUTRIENTS}, grams_per_piece=entry["grams_per_piece"],
                        micronutrients=micros.clean(entry["micronutrients"]))
        db.add(food)
    food.last_used_at = utcnow()
    db.flush()
    return food


def learn_item(db: Session, user: User, item: dict) -> UserFood | None:
    """A confirmed item that isn't a saved food -> Saved Food (general-list or AI estimate)."""
    return upsert_general(db, user, item) if item.get("general_id") else upsert_estimate(db, user, item)


def record_confirmed_items(db: Session, user: User, items: list[dict]) -> None:
    """After a log entry is confirmed: learn new foods, and mark library foods as used."""
    for it in items:
        if it.get("food_id"):
            food = get_user_food(db, user.id, it["food_id"])
            if food is not None:
                food.last_used_at = utcnow()
        else:
            learn_item(db, user, it)


def save_recipe(db: Session, user: User, payload: dict) -> UserFood:
    """Apply a confirmed save_recipe proposal (create, or replace an existing recipe)."""
    ingredient_foods: list[tuple[UserFood, dict]] = []
    for ing in payload["ingredients"]:
        food = get_user_food(db, user.id, ing["food_id"]) if ing.get("food_id") else learn_item(db, user, ing)
        if food is None:
            raise FoodError(f"Ingredient '{ing['ingredient_name']}' could not be saved")
        ingredient_foods.append((food, ing))

    recipe = find_by_name(db, user.id, payload["name"], None)
    if recipe is None:
        recipe = UserFood(user_id=user.id, name=payload["name"], name_key=name_key(payload["name"]))
        db.add(recipe)
    recipe.kind, recipe.source = "recipe", "recipe"
    recipe.brand_name = None
    recipe.ref_qty, recipe.ref_unit = payload["ref_qty"], payload["ref_unit"]
    for k in NUTRIENTS:
        setattr(recipe, k, payload["per_ref"][k])
    recipe.micronutrients = payload.get("per_ref_micronutrients")
    recipe.yield_pieces = payload.get("yield_pieces")
    recipe.yield_servings = payload.get("yield_servings")
    recipe.cooked_weight_g = payload.get("cooked_weight_g")
    recipe.grams_per_piece = payload.get("grams_per_piece")
    recipe.grams_per_serving = payload.get("grams_per_serving")
    recipe.last_used_at = utcnow()
    db.flush()

    recipe.ingredients = [
        RecipeIngredient(food_id=food.id, quantity=ing["quantity"], unit=ing["unit"])
        for food, ing in ingredient_foods if food.id != recipe.id
    ]
    db.flush()
    return recipe
