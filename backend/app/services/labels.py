"""Pack-label values for branded foods, from Open Food Facts.

Open Food Facts (openfoodfacts.org) is a free, open database of food labels (data under the
Open Database Licence), with no key or account. Only the search text or barcode is sent:
never anything about the user.

The app never trusts label numbers sent by the browser: applying a label re-fetches the
product here by its barcode. The user picks the product; nothing is applied automatically.
"""
import re

import httpx

from app import config
from app.services import micros

SEARCH_URL = "https://world.openfoodfacts.org/cgi/search.pl"
PRODUCT_URL = "https://world.openfoodfacts.org/api/v2/product/{code}.json"
FIELDS = ("code,product_name,product_name_en,brands,quantity,serving_size,serving_quantity,"
          "nutriments,countries_tags")
MAX_RESULTS = 8
TIMEOUT_S = 12
# Open Food Facts asks every app to name itself. The app's address, never the user's email.
USER_AGENT = f"{config.APP_NAME}/1.0 ({config.PUBLIC_APP_URL or 'local development'})"

# Open Food Facts gives minerals and vitamins per 100 g in grams; ours are mg or mcg.
_MICROS = {
    "iron_mg": ("iron_100g", 1000), "calcium_mg": ("calcium_100g", 1000),
    "magnesium_mg": ("magnesium_100g", 1000), "potassium_mg": ("potassium_100g", 1000),
    "zinc_mg": ("zinc_100g", 1000), "vitamin_c_mg": ("vitamin-c_100g", 1000),
    "vitamin_b12_mcg": ("vitamin-b12_100g", 1_000_000), "vitamin_d_mcg": ("vitamin-d_100g", 1_000_000),
    "sodium_mg": ("sodium_100g", 1000),
}
_BARCODE = re.compile(r"^\d{8,14}$")
_LIQUID = re.compile(r"\d\s*(?:ml|cl|l|litre|liter)s?\b", re.I)


class LabelLookupError(Exception):
    """Open Food Facts couldn't be reached, or the product can't be used."""


def is_barcode(text: str) -> bool:
    return bool(_BARCODE.match(text.strip()))


def _get(url: str, params: dict | None = None) -> dict:
    try:
        r = httpx.get(url, params=params, timeout=TIMEOUT_S, headers={"User-Agent": USER_AGENT})
        r.raise_for_status()
        return r.json()
    except (httpx.HTTPError, ValueError) as e:
        raise LabelLookupError(
            "Open Food Facts didn't answer. Try again in a minute, or type the label values in with the pencil."
        ) from e


def _num(value) -> float | None:
    try:
        n = float(value)
    except (TypeError, ValueError):
        return None
    return n if n >= 0 else None


def product_to_label(p: dict) -> dict | None:
    """An Open Food Facts product -> label values per 100 g/ml, or None when the label is
    missing calories or a macro (such a product can't be used)."""
    n = p.get("nutriments") or {}
    kcal = _num(n.get("energy-kcal_100g"))
    if kcal is None and (kj := _num(n.get("energy-kj_100g") or n.get("energy_100g"))) is not None:
        kcal = kj / 4.184
    macros = {k: _num(n.get(f"{off}_100g")) for k, off in
              (("protein_g", "proteins"), ("carbs_g", "carbohydrates"), ("fat_g", "fat"))}
    if kcal is None or None in macros.values():
        return None
    found = {k: _num(n.get(off)) for k, (off, _) in _MICROS.items()}
    serving = _num(p.get("serving_quantity"))
    return {
        "code": str(p.get("code") or ""),
        "name": (p.get("product_name") or p.get("product_name_en") or "").strip() or "Unnamed product",
        "brand": (p.get("brands") or "").split(",")[0].strip() or None,
        "pack": (p.get("quantity") or "").strip() or None,
        "serving_size": (p.get("serving_size") or "").strip() or None,
        "grams_per_serving": serving if serving else None,
        "in_india": "en:india" in (p.get("countries_tags") or []),
        "ref_qty": 100.0,
        "ref_unit": "ml" if _LIQUID.search(p.get("quantity") or "") else "g",
        "calories": round(kcal, 1),
        **{k: round(v, 2) for k, v in macros.items()},
        "fiber_g": round(_num(n.get("fiber_100g")) or 0, 2),
        "micronutrients": micros.clean({k: round(v * mult, 3) for k, (off, mult) in _MICROS.items()
                                        if (v := found[k]) is not None}),
    }


def search(text: str) -> list[dict]:
    """Products matching a name and brand (or a barcode), usable ones only, sold-in-India first."""
    text = text.strip()
    if not text:
        return []
    if is_barcode(text):
        label = get_label(text, missing_ok=True)
        return [label] if label else []
    data = _get(SEARCH_URL, {"search_terms": text, "search_simple": 1, "action": "process", "json": 1,
                             "page_size": 20, "fields": FIELDS})
    labels = [lab for p in data.get("products") or [] if (lab := product_to_label(p)) and lab["code"]]
    labels.sort(key=lambda lab: not lab["in_india"])       # stable: keeps Open Food Facts' own order
    return labels[:MAX_RESULTS]


def get_label(code: str, missing_ok: bool = False) -> dict | None:
    """One product's label values by barcode."""
    if not is_barcode(code):
        raise LabelLookupError("That isn't a barcode (8 to 14 digits).")
    data = _get(PRODUCT_URL.format(code=code.strip()), {"fields": FIELDS})
    product = data.get("product") if data.get("status") in (1, "1", "success") else None
    label = product_to_label(product) if product else None
    if label is None and not missing_ok:
        raise LabelLookupError("Open Food Facts has no complete label for that product.")
    if label is not None:
        label["code"] = label["code"] or code.strip()
    return label
