"""Micronutrient dicts ({"iron_mg": 1.2, ...}): cleaning, scaling and summing.

Values may be missing (the LLM didn't estimate them, or older entries); missing is
treated as "unknown", never as a fake zero, until totals are added up.
"""
from app.config import MICRONUTRIENT_KEYS


def clean(d: dict | None) -> dict | None:
    """Keep known keys with non-negative numeric values; None if nothing is left."""
    if not d:
        return None
    out = {}
    for k in MICRONUTRIENT_KEYS:
        v = d.get(k)
        if isinstance(v, (int, float)) and not isinstance(v, bool) and v >= 0:
            out[k] = round(float(v), 3)
    return out or None


def scale(d: dict | None, factor: float) -> dict | None:
    if not d:
        return None
    return {k: round(v * factor, 3) for k, v in d.items() if v is not None}


def total(dicts) -> dict:
    """Sum of known values per key across items; keys nobody reported are absent."""
    out: dict[str, float] = {}
    for d in dicts:
        for k, v in (d or {}).items():
            if v is not None and k in MICRONUTRIENT_KEYS:
                out[k] = out.get(k, 0) + v
    return {k: round(v, 2) for k, v in out.items()}
