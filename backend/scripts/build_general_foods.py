"""Build app/data/general_foods.json from the curated list (general_foods_spec.py) and USDA data.

The numbers come from USDA FoodData Central, SR Legacy (April 2018), which is public domain
(CC0). Download the CSV zip from https://fdc.nal.usda.gov/download-datasets, unzip it, then:

    .venv\\Scripts\\python scripts/build_general_foods.py <folder with food.csv>

Names that aren't found are listed with the closest USDA descriptions, and nothing is written.
"""
import csv
import difflib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from general_foods_spec import FOODS  # noqa: E402

OUT = Path(__file__).resolve().parents[1] / "app" / "data" / "general_foods.json"

# USDA nutrient id -> our key (per 100 g). Vitamin D and B12 are in µg, as we store them.
MACROS = {1008: "calories", 1003: "protein_g", 1005: "carbs_g", 1004: "fat_g", 1079: "fiber_g"}
MICROS = {1089: "iron_mg", 1087: "calcium_mg", 1090: "magnesium_mg", 1092: "potassium_mg", 1095: "zinc_mg",
          1162: "vitamin_c_mg", 1178: "vitamin_b12_mcg", 1114: "vitamin_d_mcg", 1093: "sodium_mg"}
# Household measures read from USDA portions (modifier text -> our unit).
MEASURES = {"cup": "cup", "tbsp": "tbsp", "tablespoon": "tbsp", "tsp": "tsp", "teaspoon": "tsp"}


def read(folder: Path, name: str):
    with open(folder / name, encoding="utf-8") as f:
        yield from csv.DictReader(f)


def slug(name: str, state: str | None) -> str:
    base = "".join(c if c.isalnum() else "-" for c in name.lower()).strip("-")
    return f"{base}-{state}" if state else base


def main(folder: Path) -> None:
    by_desc = {r["description"]: int(r["fdc_id"]) for r in read(folder, "food.csv")}
    missing = [f["usda"] for f in FOODS if f["usda"] not in by_desc]
    if missing:
        for d in missing:
            print(f"NOT FOUND: {d}\n   closest: {difflib.get_close_matches(d, by_desc, 4, 0.5)}")
        sys.exit(1)

    wanted = {by_desc[f["usda"]] for f in FOODS}
    nutrients: dict[int, dict] = {i: {} for i in wanted}
    for r in read(folder, "food_nutrient.csv"):
        fdc, nid = int(r["fdc_id"]), int(r["nutrient_id"])
        if fdc in wanted and (nid in MACROS or nid in MICROS) and r["amount"]:
            nutrients[fdc][nid] = float(r["amount"])
    portions: dict[int, list[tuple[str, float]]] = {i: [] for i in wanted}
    for r in read(folder, "food_portion.csv"):
        fdc = int(r["fdc_id"])
        if fdc in wanted and r["gram_weight"] and float(r["amount"] or 1) == 1:
            portions[fdc].append((r["modifier"].strip().lower(), float(r["gram_weight"])))

    out, seen = [], set()
    for f in FOODS:
        fdc = by_desc[f["usda"]]
        n = nutrients[fdc]
        if 1008 not in n:
            sys.exit(f"No calories for {f['usda']}")
        key = slug(f["name"], f["state"])
        if key in seen:
            sys.exit(f"Duplicate name: {key}")
        seen.add(key)
        measures = {}
        for modifier, grams in portions[fdc]:
            unit = MEASURES.get(modifier)
            if unit and unit not in measures:
                measures[unit] = grams
        piece = f["piece"]
        if isinstance(piece, str):   # a USDA portion name such as "medium" or "large"
            match = [g for m, g in portions[fdc] if m.startswith(piece)]
            if not match:
                sys.exit(f"No '{piece}' portion for {f['usda']}: {portions[fdc]}")
            piece = match[0]
        out.append({
            "id": key,
            "name": f["name"],
            "state": f["state"],
            "aliases": f["aliases"],
            **{k: round(n.get(nid, 0.0), 2) for nid, k in MACROS.items()},
            "micronutrients": {k: round(n[nid], 3) for nid, k in MICROS.items() if nid in n},
            "grams_per_piece": piece,
            "measures": measures,
            "fdc_id": fdc,
            "usda": f["usda"],
        })

    # Every typed name (incl. plurals) must point at one food, or lookups would drop it.
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from app.services.foods import _variants
    owner: dict[str, str] = {}
    for e in out:
        for name in [e["name"], *e["aliases"]]:
            for k in _variants(name):
                if owner.setdefault(k, e["name"]) != e["name"]:
                    sys.exit(f"'{name}' ({e['name']}) clashes with {owner[k]} on '{k}'")

    # Raw/cooked pairs need both halves.
    pairs: dict[str, dict] = {}
    for e in out:
        if e["state"]:
            pairs.setdefault(e["name"], {})[e["state"]] = e["calories"]
    for name, s in sorted(pairs.items()):
        if set(s) != {"raw", "cooked"}:
            sys.exit(f"'{name}' needs both a raw and a cooked entry, has {sorted(s)}")

    OUT.write_text(json.dumps({
        "source": "USDA FoodData Central, SR Legacy (April 2018), public domain (CC0). "
                  "Built by backend/scripts/build_general_foods.py from general_foods_spec.py.",
        "foods": out,
    }, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Wrote {len(out)} foods ({len(pairs)} raw/cooked pairs) to {OUT}")


if __name__ == "__main__":
    main(Path(sys.argv[1]))
