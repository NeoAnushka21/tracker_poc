"""Daily calorie and macro target calculation.

BMR: Mifflin-St Jeor. TDEE = BMR x activity factor. Goal adjusts calories;
protein is set per kg bodyweight, fat as a share of calories, carbs fill the rest.
"""
from dataclasses import dataclass
from datetime import date

from app.config import (
    ACTIVITY_FACTORS, FAT_CALORIE_SHARE, FIBER_G_PER_1000_KCAL, GOAL_SETTINGS, KCAL_PER_G, KCAL_PER_KG_PER_WEEK,
    MAX_DEFICIT_SHARE, MICRONUTRIENTS,
)


def fiber_target_g(calorie_target: float) -> int:
    return round(calorie_target * FIBER_G_PER_1000_KCAL / 1000)


def micronutrient_targets(sex: str | None, age: int | None) -> list[dict]:
    """Daily reference value per micronutrient for this person (adult values)."""
    out = []
    for key, label, unit, kind, bands in MICRONUTRIENTS:
        a = age if age is not None else 30
        _, male, female = next((b for b in bands if a <= b[0]), bands[-1])
        out.append({"key": key, "label": label, "unit": unit, "kind": kind,
                    "target": female if sex == "female" else male})
    return out


@dataclass
class Targets:
    bmr: int
    tdee: int
    daily_calorie_target: int
    protein_target_g: int
    carbs_target_g: int
    fat_target_g: int


def age_on(dob: date, today: date) -> int:
    return today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))


def mifflin_st_jeor(weight_kg: float, height_cm: float, age: int, sex: str) -> float:
    base = 10 * weight_kg + 6.25 * height_cm - 5 * age
    return base + 5 if sex == "male" else base - 161


def calculate_targets(
    *, weight_kg: float, height_cm: float, age: int, sex: str, activity_level: str, goal_type: str,
    pace_kg_per_week: float | None = None, no_deficit: bool = False,
) -> Targets:
    """`pace_kg_per_week` (optional, "about you"): calories = maintenance -/+ 1,100 kcal per kg a
    week instead of the goal's percentage; a deficit is capped at MAX_DEFICIT_SHARE.
    `no_deficit` (pregnant or breastfeeding): never below maintenance."""
    bmr = mifflin_st_jeor(weight_kg, height_cm, age, sex)
    tdee = bmr * ACTIVITY_FACTORS[activity_level]
    calorie_multiplier, protein_per_kg = GOAL_SETTINGS[goal_type]
    calories = tdee * calorie_multiplier
    if pace_kg_per_week:
        change = pace_kg_per_week * KCAL_PER_KG_PER_WEEK
        calories = tdee - min(change, tdee * MAX_DEFICIT_SHARE) if calorie_multiplier < 1 else tdee + change
    if no_deficit:
        calories = max(calories, tdee)
    calories = round(calories / 10) * 10

    protein_g = round(weight_kg * protein_per_kg)
    fat_g = round(calories * FAT_CALORIE_SHARE / KCAL_PER_G["fat"])
    remaining_kcal = calories - protein_g * KCAL_PER_G["protein"] - fat_g * KCAL_PER_G["fat"]
    carbs_g = max(0, round(remaining_kcal / KCAL_PER_G["carbs"]))

    return Targets(
        bmr=round(bmr),
        tdee=round(tdee),
        daily_calorie_target=calories,
        protein_target_g=protein_g,
        carbs_target_g=carbs_g,
        fat_target_g=fat_g,
    )
