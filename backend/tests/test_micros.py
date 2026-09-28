"""Fiber target, micronutrient targets and totals, and the add-column migration."""
from sqlalchemy import text

from app.db import add_missing_columns, engine
from app.nutrition import fiber_target_g, micronutrient_targets
from app.services import micros
from tests.test_foods import ATTA, CHICKEN, OIL, chat_propose, foods_by_name, library_item, log_and_confirm

CHICKEN_MICROS = {**CHICKEN, "micronutrients": {
    "iron_mg": 1.0, "calcium_mg": 15, "magnesium_mg": 29, "potassium_mg": 256, "zinc_mg": 1.0,
    "vitamin_c_mg": 0, "vitamin_b12_mcg": 0.3, "vitamin_d_mcg": None, "sodium_mg": 74,
}}


def test_fiber_target_is_14g_per_1000_kcal():
    assert fiber_target_g(2000) == 28
    assert fiber_target_g(1920) == 27


def test_micronutrient_targets_depend_on_sex_and_age():
    women = {t["key"]: t["target"] for t in micronutrient_targets("female", 28)}
    men = {t["key"]: t["target"] for t in micronutrient_targets("male", 45)}
    older_women = {t["key"]: t["target"] for t in micronutrient_targets("female", 60)}
    assert (women["iron_mg"], men["iron_mg"], older_women["iron_mg"]) == (18, 8, 8)
    assert (women["magnesium_mg"], men["magnesium_mg"]) == (310, 420)
    assert older_women["calcium_mg"] == 1200
    sodium = next(t for t in micronutrient_targets("male", 30) if t["key"] == "sodium_mg")
    assert sodium["kind"] == "limit"


def test_clean_drops_unknown_keys_and_bad_values():
    assert micros.clean({"iron_mg": 2, "bogus": 5, "zinc_mg": -1, "sodium_mg": None, "calcium_mg": True}) == {"iron_mg": 2.0}
    assert micros.clean({"bogus": 1}) is None


def test_daily_summary_has_fiber_target_and_micros(client, user, fake_llm):
    log_and_confirm(client, fake_llm, [CHICKEN_MICROS])
    day = client.get("/api/dashboard/daily").json()
    assert day["targets"]["fiber_g"] == fiber_target_g(day["targets"]["calories"])
    assert "fiber_g" in day["remaining"]
    m = {n["key"]: n for n in day["micronutrients"]["nutrients"]}
    assert m["potassium_mg"]["consumed"] == 256
    assert m["vitamin_d_mcg"]["consumed"] == 0          # unknown counts as nothing eaten
    assert (day["micronutrients"]["items_with_data"], day["micronutrients"]["items_total"]) == (1, 1)


def test_library_scales_micros_in_code(client, user, fake_llm):
    log_and_confirm(client, fake_llm, [CHICKEN_MICROS])
    food = foods_by_name(client)["chicken breast, cooked"]
    assert food["micronutrients"]["potassium_mg"] == 256          # stored per 100 g
    action = chat_propose(client, fake_llm, "propose_entry", {
        "summary": "m", "eaten_at": None, "meal_type": None,
        "items": [library_item(food["id"], 50, "g")],
    })
    assert action["payload"]["items"][0]["micronutrients"]["potassium_mg"] == 128


def test_recipe_micros_are_per_piece(client, user, fake_llm):
    atta = {**ATTA, "micronutrients": {"iron_mg": 4.0, "magnesium_mg": 120}}
    action = chat_propose(client, fake_llm, "propose_recipe", {
        "name": "Chapati", "ingredients": [atta, OIL],
        "yield_pieces": 4, "yield_servings": None, "cooked_weight_g": None,
    })
    assert action["payload"]["per_ref_micronutrients"] == {"iron_mg": 1.0, "magnesium_mg": 30.0}
    client.post(f"/api/actions/{action['id']}/confirm")
    assert foods_by_name(client)["Chapati"]["micronutrients"]["iron_mg"] == 1.0


def test_add_missing_columns_upgrades_an_old_database(client):
    with engine.begin() as conn:
        conn.execute(text('ALTER TABLE user_foods DROP COLUMN micronutrients'))
    assert add_missing_columns() == ["user_foods.micronutrients"]
    assert add_missing_columns() == []
