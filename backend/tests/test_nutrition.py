from datetime import date, datetime

import pytest

from app.nutrition import age_on, calculate_targets, mifflin_st_jeor
from app.timeutil import infer_meal_type, local_day_bounds_utc


def test_mifflin_st_jeor():
    assert mifflin_st_jeor(80, 180, 30, "male") == 1780
    assert mifflin_st_jeor(60, 165, 30, "female") == pytest.approx(1320.25)


def test_age_on_handles_birthday_not_yet_reached():
    assert age_on(date(1995, 6, 15), date(2026, 6, 14)) == 30
    assert age_on(date(1995, 6, 15), date(2026, 6, 15)) == 31


def test_weight_loss_targets():
    t = calculate_targets(weight_kg=80, height_cm=180, age=30, sex="male",
                          activity_level="moderate", goal_type="weight_loss")
    assert t.bmr == 1780
    assert t.tdee == 2759
    assert t.daily_calorie_target == 2210          # 20% deficit, rounded to 10
    assert t.protein_target_g == 160               # 2.0 g/kg
    assert t.fat_target_g == 61                    # 25% of kcal
    assert t.carbs_target_g == 255                 # remainder
    macro_kcal = t.protein_target_g * 4 + t.carbs_target_g * 4 + t.fat_target_g * 9
    assert abs(macro_kcal - t.daily_calorie_target) <= 5


def test_gain_goal_is_a_surplus():
    kwargs = dict(weight_kg=70, height_cm=175, age=25, sex="female", activity_level="light")
    gain = calculate_targets(goal_type="muscle_gain", **kwargs)
    loss = calculate_targets(goal_type="weight_loss", **kwargs)
    assert gain.daily_calorie_target > gain.tdee > loss.daily_calorie_target


@pytest.mark.parametrize("hour,meal", [
    (4, "evening_snack"), (5, "breakfast"), (9, "breakfast"), (10, "morning_snack"), (11, "morning_snack"),
    (12, "lunch"), (14, "lunch"), (15, "evening_snack"), (18, "evening_snack"), (19, "dinner"),
    (22, "dinner"), (23, "evening_snack"),
])
def test_meal_windows(hour, meal):
    assert infer_meal_type(datetime(2026, 1, 1, hour, 30)) == meal


def test_local_day_bounds_utc_for_india():
    start, end = local_day_bounds_utc(date(2026, 9, 28), "Asia/Kolkata")
    assert start == datetime(2026, 9, 27, 18, 30)
    assert end == datetime(2026, 9, 28, 18, 30)


def test_strip_leading_quantity_only_when_it_is_the_items_quantity():
    from app.llm.tools import strip_leading_quantity as strip
    assert strip("50 g brown rice, raw", 50) == "brown rice, raw"
    assert strip("2 piece eggs, large", 2) == "eggs, large"
    assert strip("150g chicken", 150) == "chicken"
    assert strip("7 grain bread", 2) == "7 grain bread"
