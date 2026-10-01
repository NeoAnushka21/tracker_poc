"""Branded items on a chat card: the pack label first, the AI's estimate as the fallback
(owner's design, 2026-10-01).

When MacBro proposes a food with a brand that isn't a saved food yet, Open Food Facts is searched
before the card is shown and each product is scored against what the user typed:

- sure: one product clearly is it (the brand, every word of the name, a complete label, sold in
  India, and no other close match with different numbers). The card shows only that one and
  asks "Is this it?"; "Not this one" shows the next ones.
- choose: the best few products to pick from; "None of these" shows the next ones.
- none: nothing usable found. unavailable: Open Food Facts didn't answer in time (the card
  offers "Find the label" to try again). Either way the AI's estimate stays, marked
  "check label", as before.

Nothing changes until the user taps a product (`pick`): the item then takes the label's numbers
and, once the card is confirmed, the saved food counts as label-checked. A barcode scanned in the
chat is an exact match. The AI's numbers stay on the item under "estimate", so "none of these"
can put them back. Searches are cached for everyone (models.LabelCache): public data only.
"""
import re
from concurrent.futures import ThreadPoolExecutor, wait
from datetime import timedelta

from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.orm import Session

from app import config
from app.models import LabelCache, PendingAction, User, utcnow
from app.services import labels, micros
from app.services.foods import MASS_UNITS, NUTRIENTS, edit_distance, name_key, normalize_unit, typo_limit

SURE, CHOOSE, NONE, UNAVAILABLE = "sure", "choose", "none", "unavailable"
MAX_OPTIONS = 8              # the first 1-3 are shown, "none of these" shows the next ones
SAME_NUMBERS = 0.05          # two products within 5% on every number are the same label to the user

# Words that say nothing about which product it is.
_FILLER = {"the", "of", "and", "with", "a", "an", "in", "pack", "packet", "pouch", "bottle", "jar", "box",
           "tin", "can", "g", "gm", "gms", "kg", "ml", "l", "ltr", "x", "pc", "pcs", "new", "brand"}


class LabelPickError(Exception):
    """The pick can't be applied (unknown product, or the amount can't be weighed)."""


# --- matching -----------------------------------------------------------------------

def _words(text: str | None) -> list[str]:
    out = []
    for w in re.findall(r"[a-z0-9]+", (text or "").lower()):
        if w.isdigit() or w in _FILLER:
            continue
        if len(w) > 3 and w.endswith("s") and not w.endswith("ss"):
            w = w[:-1]
        out.append(w)
    return out


def _same(a: str, b: str) -> bool:
    if a == b:
        return True
    limit = min(typo_limit(a), typo_limit(b))
    return bool(limit) and a[0] == b[0] and edit_distance(a, b, limit) <= limit


def _covered(wanted: list[str], have: list[str]) -> tuple[int, set[int]]:
    """How many of `wanted` are in `have` (small typos allowed; 'nutri choice' = 'nutrichoice'),
    and which positions of `have` they used."""
    pool = [(w, {i}) for i, w in enumerate(have)] + [(have[i] + have[i + 1], {i, i + 1}) for i in range(len(have) - 1)]

    def find(word: str) -> set[int] | None:
        return next((idx for w, idx in pool if _same(word, w)), None)

    count, used, i = 0, set(), 0
    while i < len(wanted):
        if i + 1 < len(wanted) and (idx := find(wanted[i] + wanted[i + 1])) is not None:
            count, used, i = count + 2, used | idx, i + 2
            continue
        if (idx := find(wanted[i])) is not None:
            count, used = count + 1, used | idx
        i += 1
    return count, used


def score(label: dict, brand: str | None, name: str) -> dict:
    """How well a product fits the brand and name the user gave."""
    brand_words = _words(brand)
    name_words = [w for w in _words(name) if not any(_same(w, b) for b in brand_words)]
    product_words = [w for w in _words(label["name"]) if not any(_same(w, b) for b in brand_words)]
    brand_pool = _words(label.get("brands") or label.get("brand")) + _words(label["name"])
    brand_ok = not brand_words or _covered(brand_words, brand_pool)[0] == len(brand_words)
    hits, used = _covered(name_words, product_words)
    coverage = hits / len(name_words) if name_words else 1.0
    extra = len(product_words) - len(used)
    return {
        "brand_ok": brand_ok, "coverage": coverage, "extra": extra,
        "value": 2 * brand_ok + 2 * coverage + 0.5 * bool(label.get("in_india")) - 0.15 * min(extra, 6),
    }


def _close(a: dict, b: dict) -> bool:
    return all(abs(a[k] - b[k]) <= SAME_NUMBERS * max(a[k], b[k], 1) for k in ("calories", "protein_g", "carbs_g", "fat_g"))


def rank(found: list[dict], brand: str | None, name: str) -> tuple[str, list[dict]]:
    """Open Food Facts results -> (status, the plausible products, best first)."""
    scored, seen = [], set()
    for lab in found:
        s = score(lab, brand, name)
        if not s["brand_ok"] or (s["coverage"] == 0 and _words(name)):
            continue          # another brand, or nothing of the name: not worth showing
        key = (tuple(_words(lab["name"])), round(lab["calories"]), round(lab["protein_g"]), round(lab["fat_g"]))
        if key in seen:       # the same product in another pack size
            continue
        seen.add(key)
        scored.append((s, lab))
    scored.sort(key=lambda x: -x[0]["value"])           # stable: ties keep Open Food Facts' order
    options = [lab for _, lab in scored[:MAX_OPTIONS]]
    if not options:
        return NONE, []
    top_s, top = scored[0]
    full = [lab for s, lab in scored if s["coverage"] == 1]
    sure = (top_s["coverage"] == 1 and top_s["extra"] <= 1 and top.get("in_india")
            and all(_close(top, lab) for lab in full))
    return (SURE if sure else CHOOSE), options


# --- Open Food Facts, with the shared cache --------------------------------------------

def _cached(db: Session, key: str) -> list[dict] | None:
    row = db.get(LabelCache, key)
    if row is not None and row.fetched_at > utcnow() - timedelta(days=config.LABEL_CACHE_DAYS):
        return row.labels
    return None


def _store(db: Session, key: str, found: list[dict]) -> None:
    """Insert or refresh, safe when two people search the same thing at once."""
    insert = pg_insert if db.get_bind().dialect.name == "postgresql" else sqlite_insert
    stmt = insert(LabelCache.__table__).values(key=key, labels=found, fetched_at=utcnow())
    db.execute(stmt.on_conflict_do_update(index_elements=["key"],
                                          set_={"labels": stmt.excluded.labels, "fetched_at": stmt.excluded.fetched_at}))


def _search_key(text: str) -> str:
    return "q:" + " ".join(_words(text))[:280]


def search_many(db: Session, queries: list[str]) -> dict[str, list[dict] | None]:
    """Each query -> its labels (None when Open Food Facts didn't answer). Uncached queries are
    fetched side by side, with a short timeout, so a slow service never holds a card up for long."""
    out: dict[str, list[dict] | None] = {}
    missing = []
    for q in dict.fromkeys(queries):
        hit = _cached(db, _search_key(q))
        if hit is not None:
            out[q] = hit
        else:
            missing.append(q)
    if missing:
        pool = ThreadPoolExecutor(max_workers=min(4, len(missing)))
        futures = {q: pool.submit(labels.search, q, config.LABEL_AUTO_TIMEOUT_S) for q in missing}
        wait(futures.values(), timeout=config.LABEL_AUTO_TIMEOUT_S + 2)
        pool.shutdown(wait=False)      # a straggler finishes on its own; its answer is dropped
        for q, f in futures.items():
            try:
                out[q] = f.result(timeout=0)
            except Exception:  # LabelLookupError, a timeout, anything: fall back to the estimate
                out[q] = None
                continue
            _store(db, _search_key(q), out[q])
    return out


def by_barcode(db: Session, code: str) -> dict | None:
    """One product's label by barcode (cached). Raises LabelLookupError when unreachable."""
    key = f"code:{code}"
    hit = _cached(db, key)
    if hit is None:
        label = labels.get_label(code, missing_ok=True, timeout=config.LABEL_AUTO_TIMEOUT_S)
        hit = [label] if label else []
        _store(db, key, hit)
    return hit[0] if hit else None


# --- the card's items ------------------------------------------------------------------

def _query(item: dict) -> str:
    return f"{item.get('brand_name') or ''} {item['ingredient_name']}".strip()


def wants_label(item: dict) -> bool:
    """A branded food the AI estimated (saved foods and general-list foods already have numbers)."""
    return item.get("source") == "estimate" and bool((item.get("brand_name") or "").strip())


def label_item(item: dict, label: dict) -> dict:
    """The item with the label's numbers for its amount. Grams come from the amount, the label's
    serving weight, or the AI's weight for one piece (marked, so the card can say so)."""
    u, mult = normalize_unit(item["unit"])
    qty = item["quantity"] * mult
    estimated = False
    if u in MASS_UNITS:
        grams = qty
    elif u == "serving" and label.get("grams_per_serving"):
        grams = qty * label["grams_per_serving"]
    elif item.get("unit_weight_g"):
        grams, estimated = qty * item["unit_weight_g"], True
    else:
        raise LabelPickError(f"I don't know how much one {item['unit']} weighs. Tell MacBro the amount in grams.")
    f = grams / label["ref_qty"]
    estimate = item.get("estimate") or {k: item.get(k) for k in (*NUTRIENTS, "micronutrients")}
    return {
        **item,
        **{k: round((label.get(k) or 0) * f, 1) for k in NUTRIENTS},
        "micronutrients": micros.scale(label.get("micronutrients"), f),
        "brand_name": item.get("brand_name") or label.get("brand"),
        "source": "label",
        "off_code": label["code"],
        "label": label,
        "weight_estimated": estimated,
        "estimate": estimate,
    }


def _unlabelled(item: dict) -> dict:
    """The item with the AI's numbers back."""
    est = item.get("estimate")
    out = {k: v for k, v in item.items() if k not in ("off_code", "label", "weight_estimated")}
    if est:
        out.update(est)
    out["source"] = "estimate"
    return out


def _previous_picks(db: Session, user: User) -> dict[str, dict]:
    """Labels the user already picked on still-open cards, by food, so "make it 20 g" keeps them."""
    from app.services.actions import open_actions
    picks = {}
    for a in open_actions(db, user.id):
        for it in (a.payload or {}).get("items") or []:
            if it.get("label") and (it.get("label_match") or {}).get("picked"):
                picks[name_key(it["ingredient_name"], it.get("brand_name"))] = it["label"]
    return picks


def attach(db: Session, user: User, items: list[dict], scanned_code: str | None = None) -> list[dict]:
    """Add `label_match` (status + options) to each branded estimate. Called while the card is
    made; never raises (Open Food Facts trouble just leaves the estimate)."""
    targets = [i for i, it in enumerate(items) if wants_label(it)]
    scanned, scanned_at = None, None
    if scanned_code:
        try:
            scanned = by_barcode(db, scanned_code)
        except labels.LabelLookupError:
            scanned = None
        if scanned is not None:
            # The scanned product is one of the foods on the card: the estimate it fits best.
            estimates = [i for i, it in enumerate(items) if it.get("source") == "estimate"]
            fits = sorted(estimates, key=lambda i: -score(scanned, items[i].get("brand_name"), items[i]["ingredient_name"])["value"])
            if fits and fits[0] not in targets:
                targets.append(fits[0])
            scanned_at = fits[0] if fits else None
    if not targets:
        return items

    picks = _previous_picks(db, user)
    found = search_many(db, [_query(items[i]) for i in targets])     # usually cached for a repeat

    out = list(items)
    for i in targets:
        it = items[i]
        results = found.get(_query(it))
        status, options = (UNAVAILABLE, []) if results is None else rank(results, it.get("brand_name"), it["ingredient_name"])
        # Already chosen by the user: scanned (or picked in the chat's pack finder) with this
        # message, or picked on the card this one replaces. It comes ready on the card; the
        # other products stay one tap away ("Change").
        chosen, how = None, "search"
        if scanned is not None and i == scanned_at:
            chosen, how = scanned, "barcode"
        elif (carried := picks.get(name_key(it["ingredient_name"], it.get("brand_name")))) is not None:
            chosen, how = carried, "picked"
        if chosen is not None:
            status = SURE
            options = [chosen, *[lab for lab in options if lab["code"] != chosen["code"]]][:MAX_OPTIONS]
        match = {"status": status, "options": options, "query": _query(it), "how": how, "picked": None}
        if chosen is not None:
            try:
                out[i] = {**label_item(it, chosen), "label_match": {**match, "picked": chosen["code"]}}
                continue
            except LabelPickError:
                pass          # the amount can't be weighed: the user picks once it's in grams
        out[i] = {**it, "label_match": match}
    return out


# --- the user's taps on the card -------------------------------------------------------

def _editable(action: PendingAction, index: int) -> tuple[dict, list[dict]]:
    if action.action_type not in ("create", "edit"):
        raise LabelPickError("This card has no foods to check")
    payload = dict(action.payload)
    items = [dict(it) for it in payload.get("items") or []]
    if not 0 <= index < len(items) or "label_match" not in items[index]:
        raise LabelPickError("That food has no pack label to choose")
    return payload, items


def _save(action: PendingAction, payload: dict, items: list[dict]) -> None:
    from app.services.logs import sum_items
    payload["items"] = items
    payload["totals"] = sum_items(items)
    action.payload = payload          # a new dict, so the JSON column is written


def pick(action: PendingAction, index: int, code: str | None) -> None:
    """The user tapped a product (code), or "none of these" (None: the AI's estimate stays).
    Only products the server found itself can be picked; the browser sends just the barcode."""
    payload, items = _editable(action, index)
    it = items[index]
    match = dict(it["label_match"])
    if code is None:
        items[index] = {**_unlabelled(it), "label_match": {**match, "picked": None, "declined": True}}
    else:
        label = next((lab for lab in match["options"] if lab["code"] == code), None)
        if label is None:
            raise LabelPickError("That product wasn't one of the choices")
        items[index] = {**label_item(_unlabelled(it), label), "label_match": {**match, "picked": code, "declined": False}}
    _save(action, payload, items)


def search_again(db: Session, action: PendingAction, index: int) -> None:
    """"Find the label" after Open Food Facts didn't answer: search once more (no short cut)."""
    payload, items = _editable(action, index)
    it = items[index]
    query = it["label_match"].get("query") or _query(it)
    try:
        found = labels.search(query)
    except labels.LabelLookupError:
        found = None
    if found is None:
        status, options = UNAVAILABLE, []
    else:
        _store(db, _search_key(query), found)
        status, options = rank(found, it.get("brand_name"), it["ingredient_name"])
    items[index] = {**_unlabelled(it), "label_match": {**it["label_match"], "status": status, "options": options,
                                                      "picked": None, "declined": False}}
    _save(action, payload, items)
