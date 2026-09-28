"""Body metrics from the profile: BMI and an estimated body-fat percentage.

Both are screening estimates, not diagnoses, and the UI says so. Nothing here guesses a
missing value: if an input is missing or the result is implausible, the caller gets a status
explaining why instead of a number.
"""
import math

from app.config import BMI_CATEGORIES, BODY_FAT_PLAUSIBLE

NAVY_METHOD = "US Navy circumference method (Hodgdon & Beckett, 1984)"
# Reported agreement with lab methods is roughly ±3–4 percentage points for most adults.
NAVY_TYPICAL_ERROR = 3.5
# Measurements taken this far apart are flagged: body fat needs them from about the same time.
SAME_SESSION_DAYS = 30


def bmi(weight_kg: float | None, height_cm: float | None) -> dict:
    if not weight_kg or not height_cm:
        missing = [n for n, v in (("weight", weight_kg), ("height", height_cm)) if not v]
        return {"status": "missing", "missing": missing}
    # Categorise the one-decimal value people see (WHO bands are written to one decimal),
    # so "30.0" is never shown as "Overweight".
    value = round(weight_kg / (height_cm / 100) ** 2, 1)
    category = next(label for upper, label in BMI_CATEGORIES if value < upper)
    return {"status": "ok", "value": value, "category": category,
            "note": "WHO adult categories. BMI doesn't tell muscle from fat."}


def body_fat_navy(sex: str | None, height_cm: float | None, neck_cm: float | None,
                  waist_cm: float | None, hips_cm: float | None) -> dict:
    """US Navy equations (metric form, lengths in cm, log base 10):

    men:   %BF = 495 / (1.0324 − 0.19077·log10(waist − neck) + 0.15456·log10(height)) − 450
    women: %BF = 495 / (1.29579 − 0.35004·log10(waist + hips − neck) + 0.22100·log10(height)) − 450
    """
    if sex not in ("male", "female"):
        return {"status": "missing", "missing": ["sex (in your profile)"], "method": NAVY_METHOD}
    needed = [("height", height_cm), ("neck", neck_cm), ("waist", waist_cm)]
    if sex == "female":
        needed.append(("hips", hips_cm))
    missing = [name for name, v in needed if not v]
    if missing:
        return {"status": "missing", "missing": missing, "method": NAVY_METHOD}

    if sex == "male":
        span = waist_cm - neck_cm
        if span <= 0:
            return {"status": "implausible", "reason": "Your waist must be larger than your neck. Please re-check both.",
                    "method": NAVY_METHOD}
        density_term = 1.0324 - 0.19077 * math.log10(span) + 0.15456 * math.log10(height_cm)
    else:
        span = waist_cm + hips_cm - neck_cm
        if span <= 0:
            return {"status": "implausible", "reason": "Waist plus hips must be larger than your neck. Please re-check them.",
                    "method": NAVY_METHOD}
        density_term = 1.29579 - 0.35004 * math.log10(span) + 0.22100 * math.log10(height_cm)
    value = 495 / density_term - 450

    low, high = BODY_FAT_PLAUSIBLE[sex]
    if not low <= value <= high:
        return {"status": "implausible", "method": NAVY_METHOD,
                "reason": "These measurements give a result outside the human range, so they're probably off. "
                          "Please re-measure (see the tips for each measurement)."}
    return {"status": "ok", "value": round(value, 1), "method": NAVY_METHOD,
            "typical_error": NAVY_TYPICAL_ERROR}
