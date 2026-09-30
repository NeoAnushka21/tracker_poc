"""Monthly check of the general food list against USDA (run by .github/workflows/usda-refresh.yml).

1. Downloads the USDA SR Legacy CSV, rebuilds app/data/general_foods.json and reports any food
   whose numbers changed. SR Legacy has been frozen since 2018, so this is a safety net.
2. Lists USDA Foundation Foods (the part USDA still adds to, about twice a year) that are new
   or removed since the last check, as candidates for the list. Adding one is a manual step:
   it needs our short name, aliases and raw/cooked choice in general_foods_spec.py.

Writes the report to the path given (the pull request text) and updates the snapshot of seen
Foundation Foods (app/data/usda_foundation_seen.json). Free: the USDA API key is optional
(env USDA_API_KEY from api.data.gov, else DEMO_KEY, which allows ~10 requests an hour).

    python scripts/check_usda_updates.py report.md
"""
import io
import json
import os
import sys
import tempfile
import urllib.request
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_general_foods  # noqa: E402

SR_LEGACY_ZIP = "https://fdc.nal.usda.gov/fdc-datasets/FoodData_Central_sr_legacy_food_csv_2018-04.zip"
LIST_API = "https://api.nal.usda.gov/fdc/v1/foods/list"
DATA = Path(__file__).resolve().parents[1] / "app" / "data"
SEEN = DATA / "usda_foundation_seen.json"
COMPARED = ("calories", "protein_g", "carbs_g", "fat_g", "fiber_g", "grams_per_piece", "measures", "micronutrients")


def fetch(url: str, body: dict | None = None) -> bytes:
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json",
                                                          "User-Agent": "OmniAI food list check"})
    with urllib.request.urlopen(req, timeout=120) as r:
        return r.read()


def rebuild() -> list[str]:
    """Rebuild general_foods.json from the latest download; lines for foods whose values changed."""
    old = {e["id"]: e for e in json.loads(build_general_foods.OUT.read_text(encoding="utf-8"))["foods"]}
    with tempfile.TemporaryDirectory() as tmp:
        zipfile.ZipFile(io.BytesIO(fetch(SR_LEGACY_ZIP))).extractall(tmp)
        [folder] = [p.parent for p in Path(tmp).rglob("food.csv")]
        build_general_foods.main(folder)
    new = {e["id"]: e for e in json.loads(build_general_foods.OUT.read_text(encoding="utf-8"))["foods"]}
    lines = []
    for fid in sorted(old.keys() | new.keys()):
        a, b = old.get(fid), new.get(fid)
        if a is None or b is None:
            lines.append(f"- `{fid}`: {'added' if a is None else 'removed'}")
            continue
        changed = [k for k in COMPARED if a.get(k) != b.get(k)]
        if changed:
            lines.append(f"- `{fid}`: " + ", ".join(f"{k} {a.get(k)} → {b.get(k)}" for k in changed))
    return lines


def foundation_foods() -> dict[str, str]:
    """{fdc id: description} for every USDA Foundation Food, via the free list API."""
    key = os.environ.get("USDA_API_KEY") or "DEMO_KEY"
    out, page = {}, 1
    while True:
        rows = json.loads(fetch(f"{LIST_API}?api_key={key}",
                                {"dataType": ["Foundation"], "pageSize": 200, "pageNumber": page}))
        out.update({str(r["fdcId"]): r["description"] for r in rows})
        if len(rows) < 200:
            return out
        page += 1


def main(report_path: Path) -> None:
    changed = rebuild()
    now = foundation_foods()
    seen = json.loads(SEEN.read_text(encoding="utf-8")) if SEEN.exists() else {}
    added = sorted((d, i) for i, d in now.items() if i not in seen)
    removed = sorted((d, i) for i, d in seen.items() if i not in now)
    SEEN.write_text(json.dumps(dict(sorted(now.items(), key=lambda kv: kv[1])), indent=1, ensure_ascii=False) + "\n",
                    encoding="utf-8")

    parts = ["Monthly check of the general food list against USDA FoodData Central "
             "(`backend/scripts/check_usda_updates.py`).", ""]
    parts += ["## Numbers changed in our list", *(changed or ["None."]), ""]
    parts += ["## New USDA Foundation Foods (candidates to add)",
              *([f"- {d} (fdc {i})" for d, i in added] or ["None."]), ""]
    if added:
        parts += ["To add one: give it a short name, aliases and raw/cooked in "
                  "`backend/scripts/general_foods_spec.py`, then rebuild. Merging this PR only "
                  "records that they were seen.", ""]
    if removed:
        parts += ["## Removed from USDA Foundation Foods", *[f"- {d} (fdc {i})" for d, i in removed], ""]
    report_path.write_text("\n".join(parts), encoding="utf-8")
    print(f"{len(changed)} changed, {len(added)} new, {len(removed)} removed")


if __name__ == "__main__":
    main(Path(sys.argv[1]))
