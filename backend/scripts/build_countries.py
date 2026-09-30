"""Build app/data/countries.json (countries and their regions for the profile dropdowns).

Source: the `country-region-data` npm package (MIT licence, (c) Benjamin Keen), pinned below.
Countries are stored by ISO 3166-1 alpha-2 code; regions by name, because some small
territories have regions without a code. The licence is copied next to the data.

    .venv\\Scripts\\python scripts/build_countries.py
"""
import json
import urllib.request
from pathlib import Path

VERSION = "4.1.0"
BASE = f"https://cdn.jsdelivr.net/npm/country-region-data@{VERSION}"
OUT = Path(__file__).resolve().parents[1] / "app" / "data"


def fetch(path: str) -> bytes:
    with urllib.request.urlopen(f"{BASE}/{path}", timeout=60) as r:
        return r.read()


def main() -> None:
    raw = json.loads(fetch("data.json"))
    countries = sorted(
        ({"code": c["countryShortCode"], "name": c["countryName"],
          "regions": sorted({r["name"] for r in c["regions"]})} for c in raw),
        key=lambda c: c["name"],
    )
    assert len({c["code"] for c in countries}) == len(countries), "duplicate country codes"
    (OUT / "countries.json").write_text(json.dumps({
        "source": f"country-region-data {VERSION} (MIT licence, see countries.LICENSE.txt). "
                  "Built by backend/scripts/build_countries.py.",
        "countries": countries,
    }, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")
    (OUT / "countries.LICENSE.txt").write_bytes(fetch("LICENSE.txt"))
    print(f"Wrote {len(countries)} countries, {sum(len(c['regions']) for c in countries)} regions")


if __name__ == "__main__":
    main()
