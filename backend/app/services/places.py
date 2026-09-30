"""Countries and regions for the profile (dropdowns only, so values are always from this list).

Data: app/data/countries.json, built by scripts/build_countries.py from `country-region-data`
(MIT). Country = ISO 3166-1 alpha-2 code ("IN"); region = its name ("Maharashtra").
"""
import json
from functools import lru_cache
from pathlib import Path

DATA = Path(__file__).resolve().parents[1] / "data" / "countries.json"


@lru_cache(maxsize=1)
def countries() -> list[dict]:
    """[{code, name, regions: [name, ...]}, ...], sorted by name. Served to the dropdowns as is."""
    return json.loads(DATA.read_text(encoding="utf-8"))["countries"]


@lru_cache(maxsize=1)
def _by_code() -> dict[str, dict]:
    return {c["code"]: c for c in countries()}


def check(country: str, region: str | None) -> tuple[str, str | None]:
    """(country code, region or None) if both are on the list; ValueError with a readable message if not."""
    c = _by_code().get((country or "").strip().upper())
    if c is None:
        raise ValueError("Please pick your country from the list")
    region = (region or "").strip() or None
    if region is not None and region not in c["regions"]:
        raise ValueError(f"Please pick a region of {c['name']} from the list")
    return c["code"], region


def country_name(code: str | None) -> str | None:
    c = _by_code().get(code or "")
    return c["name"] if c else None
