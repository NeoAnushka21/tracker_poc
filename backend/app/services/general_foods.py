"""The built-in general food list: ~300 common foods per 100 g from USDA FoodData Central
(SR Legacy, public domain), with our own short names and aliases (incl. Indian names).
Built by scripts/build_general_foods.py; read-only, loaded once.

Lookup order everywhere is Saved Food -> this list -> the AI. Foods whose numbers change a lot
when cooked (meat, fish, rice, grains, dals) come as a raw/cooked pair, and the app asks which
one the user means instead of assuming (owner's rule, 2026-09-30).
"""
import json
import re
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path

from app.services import micros
from app.services.foods import MASS_UNITS, NUTRIENTS, FoodError, _variants, closest_saved, normalize_unit

DATA = Path(__file__).resolve().parents[1] / "data" / "general_foods.json"
SOURCE_NOTE = "USDA FoodData Central (public domain)"

# Words that say which state a food was weighed in. Names that include one ("boiled egg",
# "roasted peanuts", "dried figs") are matched as whole names first.
STATE_WORDS = {"raw": "raw", "uncooked": "raw", "dry": "raw",
               "cooked": "cooked", "boiled": "cooked", "steamed": "cooked", "grilled": "cooked",
               "roasted": "cooked", "baked": "cooked", "pressure cooked": "cooked"}
_STATE_RE = re.compile(r"\b(" + "|".join(sorted(STATE_WORDS, key=len, reverse=True)) + r")\b")
PIECE_UNITS = ("piece", "slice", "whole")


@dataclass
class Match:
    """What a typed name means in the list. `entry` is None when the state must be asked."""
    base: str
    entry: dict | None
    options: list[str] = field(default_factory=list)


@lru_cache(maxsize=1)
def _load() -> tuple[dict[str, dict], dict[str, dict], dict[str, str]]:
    """(entries by id, {base name: {state or None: entry}}, {typed key: base name})."""
    foods = json.loads(DATA.read_text(encoding="utf-8"))["foods"]
    by_id = {e["id"]: e for e in foods}
    groups: dict[str, dict] = {}
    for e in foods:
        groups.setdefault(e["name"], {})[e["state"]] = e
    index: dict[str, str] = {}
    ambiguous: set[str] = set()
    for base, group in groups.items():
        aliases = {a for e in group.values() for a in e["aliases"]}
        for name in {base, *aliases}:
            for k in _variants(name):
                if k in index and index[k] != base:
                    ambiguous.add(k)
                index[k] = base
    for k in ambiguous:
        index.pop(k, None)
    return by_id, groups, index


def get(general_id: str) -> dict | None:
    return _load()[0].get(general_id)


def display_name(entry: dict) -> str:
    return f"{entry['name']}, {entry['state']}" if entry["state"] else entry["name"]


def state_in(text: str) -> str | None:
    """'raw' / 'cooked' if the text says so ('200 g boiled rice' -> cooked), else None."""
    states = {STATE_WORDS[m] for m in _STATE_RE.findall(text.lower())}
    return states.pop() if len(states) == 1 else None


def strip_state(text: str) -> str:
    return re.sub(r"\s+", " ", _STATE_RE.sub(" ", text.lower())).strip(" ,")


def find(typed: str) -> Match | None:
    """The general food a typed name means (typos allowed), or None if it isn't on the list."""
    _, groups, index = _load()
    base = closest_saved(index, typed, strict=True)                     # whole name: "boiled egg", "dried figs"
    if base is not None:
        group = groups[base]
        if None in group:
            return Match(base, group[None])
        state = state_in(typed)
        return Match(base, group[state]) if state else Match(base, None, ["raw", "cooked"])
    state, rest = state_in(typed), strip_state(typed)
    if not state or not rest or rest == typed.lower().strip():
        return None
    base = closest_saved(index, rest, strict=True)
    if base is None:
        return None
    group = groups[base]
    return Match(base, group.get(state) or group.get(None))


def grams_for(entry: dict, qty: float, unit: str, unit_weight_g: float | None = None) -> float | None:
    """Grams in `qty unit` of this food, or None if the unit can't be converted."""
    u, mult = normalize_unit(unit)
    if u in MASS_UNITS:
        return qty * mult
    if u in PIECE_UNITS and entry["grams_per_piece"]:
        return qty * entry["grams_per_piece"]
    if u in entry["measures"]:
        return qty * entry["measures"][u]
    if unit_weight_g:
        return qty * unit_weight_g
    return None


def units_for(entry: dict) -> list[str]:
    return ["g", *(["piece"] if entry["grams_per_piece"] else []), *entry["measures"]]


def resolve_item(item: dict) -> dict:
    """A proposed item that names a general food -> its nutrients, computed here from the list."""
    entry = get(item["general_id"])
    if entry is None:
        raise FoodError(f"general_id '{item['general_id']}' isn't in general_foods. Use null and estimate instead.")
    grams = grams_for(entry, item["quantity"], item["unit"], item.get("unit_weight_g"))
    if grams is None:
        raise FoodError(f"Can't convert '{item['unit']}' for '{display_name(entry)}'. Use one of: "
                        f"{', '.join(units_for(entry))}, or set unit_weight_g.")
    f = grams / 100
    u, _ = normalize_unit(item["unit"])
    return {
        **item,
        "ingredient_name": display_name(entry),
        "brand_name": None,
        **{k: round(entry[k] * f, 1) for k in NUTRIENTS},
        "micronutrients": micros.scale(entry["micronutrients"] or None, f),
        "unit_weight_g": None if u in MASS_UNITS else round(grams / item["quantity"], 1),
        "food_id": None,
        "source": "general",
    }


def context_lines(match_text: str, skip_names: set[str], limit: int = 20) -> list[str]:
    """Lines for the AI's context: general foods named in the message (typos allowed) that the
    user hasn't saved, as 'id | name | per 100 g: kcal P C F | units'."""
    from app.services.foods import _shares_word, _stems   # the same loose matching as Saved Food
    by_id, groups, _ = _load()
    wanted = _stems(match_text)
    lines = []
    for base, group in groups.items():
        aliases = {a for e in group.values() for a in e["aliases"]}
        if not _shares_word(_stems(" ".join([base, *aliases])), wanted):
            continue
        for e in group.values():
            if display_name(e).lower() in skip_names:
                continue
            lines.append(f"{e['id']} | {display_name(e)} | per 100 g: {e['calories']:g} kcal, P {e['protein_g']:g}, "
                         f"C {e['carbs_g']:g}, F {e['fat_g']:g} | units: {', '.join(units_for(e))}")
        if len(lines) >= limit:
            break
    return lines[:limit]
