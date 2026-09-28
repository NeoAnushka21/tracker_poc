"""Food library + recipes: unit maths, learning on confirm, library-based logging, recipes."""
import pytest

from app.models import UserFood
from app.services.foods import FoodError, compute_recipe, nutrients_for, normalize_unit
from tests.conftest import tool_reply

CHICKEN = {
    "ingredient_name": "chicken breast, cooked", "brand_name": None, "quantity": 100, "unit": "g",
    "calories": 165, "protein_g": 31, "carbs_g": 0, "fat_g": 3.6, "fiber_g": 0,
    "food_id": None, "unit_weight_g": None,
}
ATTA = {
    "ingredient_name": "multigrain atta", "brand_name": "Pillsbury", "quantity": 100, "unit": "g",
    "calories": 346, "protein_g": 12, "carbs_g": 70, "fat_g": 2, "fiber_g": 11,
    "food_id": None, "unit_weight_g": None,
}
OIL = {
    "ingredient_name": "sunflower oil", "brand_name": None, "quantity": 5, "unit": "ml",
    "calories": 44, "protein_g": 0, "carbs_g": 0, "fat_g": 5, "fiber_g": 0,
    "food_id": None, "unit_weight_g": None,
}


def library_item(food_id: int, qty: float, unit: str, name: str = "x") -> dict:
    return {"ingredient_name": name, "brand_name": None, "quantity": qty, "unit": unit,
            "calories": 0, "protein_g": 0, "carbs_g": 0, "fat_g": 0, "fiber_g": 0,
            "food_id": food_id, "unit_weight_g": None}


def chat_propose(client, fake_llm, tool: str, args: dict, message: str = "msg") -> dict:
    fake_llm(tool_reply(tool, {"note": "ok", **args}))
    r = client.post("/api/chat", json={"message": message})
    assert r.status_code == 200, r.text
    return r.json()[-1]["actions"][0]


def log_and_confirm(client, fake_llm, items: list[dict]) -> dict:
    action = chat_propose(client, fake_llm, "propose_entry",
                          {"summary": "meal", "eaten_at": None, "meal_type": None, "items": items})
    assert client.post(f"/api/actions/{action['id']}/confirm").status_code == 200
    return action


def foods_by_name(client) -> dict:
    return {f["name"]: f for f in client.get("/api/foods").json()}


# --- unit maths ----------------------------------------------------------------

def make_food(**kw) -> UserFood:
    base = dict(name="f", ref_qty=100, ref_unit="g", calories=100, protein_g=10, carbs_g=10, fat_g=2,
                fiber_g=1, grams_per_piece=None, grams_per_serving=None)
    return UserFood(**{**base, **kw})


@pytest.mark.parametrize("unit,expected", [
    ("grams", ("g", 1)), ("Kg", ("g", 1000)), ("pcs", ("piece", 1)), ("Cups", ("cup", 1)),
    ("glasses", ("glass", 1)), ("L", ("ml", 1000)), ("servings", ("serving", 1)),
])
def test_normalize_unit(unit, expected):
    assert normalize_unit(unit) == expected


def test_scaling_by_weight_piece_and_serving():
    per100 = make_food(grams_per_piece=50, grams_per_serving=200)
    assert nutrients_for(per100, 50, "g")["calories"] == 50
    assert nutrients_for(per100, 0.5, "kg")["calories"] == 500
    assert nutrients_for(per100, 2, "pieces")["calories"] == 100        # 2 x 50 g
    assert nutrients_for(per100, 1, "serving")["calories"] == 200

    per_piece = make_food(ref_qty=1, ref_unit="piece", calories=96, grams_per_piece=40)
    assert nutrients_for(per_piece, 3, "piece")["calories"] == 288
    assert nutrients_for(per_piece, 80, "g")["calories"] == 192         # 80 g = 2 pieces


def test_unconvertible_unit_explains_options():
    with pytest.raises(FoodError, match="Can't convert 'bowl'"):
        nutrients_for(make_food(), 1, "bowl")


def test_compute_recipe_yields():
    ings = [{"calories": 346, "protein_g": 12, "carbs_g": 70, "fat_g": 2, "fiber_g": 11},
            {"calories": 44, "protein_g": 0, "carbs_g": 0, "fat_g": 5, "fiber_g": 0}]
    by_pieces = compute_recipe(ings, 4, None, None)
    assert (by_pieces["ref_qty"], by_pieces["ref_unit"]) == (1.0, "piece")
    assert by_pieces["per_ref"]["calories"] == 97.5
    by_weight = compute_recipe(ings, None, 3, 600)
    assert (by_weight["ref_qty"], by_weight["ref_unit"]) == (100.0, "g")
    assert by_weight["per_ref"]["calories"] == 65
    assert by_weight["grams_per_serving"] == 200
    with pytest.raises(FoodError, match="needs a yield"):
        compute_recipe(ings, None, None, None)


# --- learning foods on confirm -----------------------------------------------------

def test_confirmed_estimates_are_saved_per_100g(client, user, fake_llm):
    log_and_confirm(client, fake_llm, [{**CHICKEN, "quantity": 200, "calories": 330, "protein_g": 62, "fat_g": 7.2}])
    food = foods_by_name(client)["chicken breast, cooked"]
    assert (food["ref_qty"], food["ref_unit"], food["calories"], food["protein_g"]) == (100, "g", 165, 31)


def test_cancelled_proposals_are_not_learned(client, user, fake_llm):
    action = chat_propose(client, fake_llm, "propose_entry",
                          {"summary": "m", "eaten_at": None, "meal_type": None, "items": [CHICKEN]})
    client.post(f"/api/actions/{action['id']}/reject")
    assert client.get("/api/foods").json() == []


def test_piece_foods_keep_their_gram_weight(client, user, fake_llm):
    almonds = {**CHICKEN, "ingredient_name": "almond", "quantity": 10, "unit": "piece",
               "calories": 70, "protein_g": 2.5, "carbs_g": 2.6, "fat_g": 6, "fiber_g": 1.5, "unit_weight_g": 1.2}
    log_and_confirm(client, fake_llm, [almonds])
    food = foods_by_name(client)["almond"]
    assert (food["ref_qty"], food["ref_unit"], food["calories"], food["grams_per_piece"]) == (1, "piece", 7, 1.2)


def test_library_item_nutrients_come_from_code_not_the_model(client, user, fake_llm):
    log_and_confirm(client, fake_llm, [CHICKEN])
    food_id = foods_by_name(client)["chicken breast, cooked"]["id"]
    action = chat_propose(client, fake_llm, "propose_entry", {
        "summary": "m", "eaten_at": None, "meal_type": None,
        "items": [library_item(food_id, 50, "g", name="chicken")],
    })
    item = action["payload"]["items"][0]
    assert item["source"] == "library"
    assert item["ingredient_name"] == "chicken breast, cooked"
    assert (item["calories"], item["protein_g"]) == (82.5, 15.5)


def test_unknown_food_id_is_a_tool_error(client, user, fake_llm):
    from tests.conftest import text_reply
    provider = fake_llm(
        tool_reply("propose_entry", {"summary": "m", "eaten_at": None, "meal_type": None, "note": "",
                                     "items": [library_item(999, 1, "g")]}),
        text_reply("Sorry, let me estimate."),
    )
    client.post("/api/chat", json={"message": "x"})
    result = provider.calls[1]["messages"][-1]["content"][0]
    assert result["is_error"] and "isn't in the user's library" in result["content"]


def test_hand_edited_food_is_not_overwritten_by_estimates(client, user, fake_llm):
    log_and_confirm(client, fake_llm, [CHICKEN])
    food = foods_by_name(client)["chicken breast, cooked"]
    r = client.put(f"/api/foods/{food['id']}", json={**food, "protein_g": 32, "calories": 170})
    assert r.status_code == 200 and r.json()["source"] == "user"
    log_and_confirm(client, fake_llm, [{**CHICKEN, "calories": 150, "protein_g": 28, "fat_g": 3.2}])
    assert foods_by_name(client)["chicken breast, cooked"]["protein_g"] == 32


def test_latest_confirmed_estimate_replaces_older_estimate(client, user, fake_llm):
    log_and_confirm(client, fake_llm, [CHICKEN])
    log_and_confirm(client, fake_llm, [{**CHICKEN, "calories": 160, "protein_g": 32, "fat_g": 3.4}])
    assert foods_by_name(client)["chicken breast, cooked"]["protein_g"] == 32


# --- recipes -----------------------------------------------------------------------

def propose_chapati(client, fake_llm, oil=OIL, yield_pieces=4):
    return chat_propose(client, fake_llm, "propose_recipe", {
        "name": "Chapati", "ingredients": [ATTA, oil],
        "yield_pieces": yield_pieces, "yield_servings": None, "cooked_weight_g": None,
    })


def test_recipe_is_only_saved_on_confirm(client, user, fake_llm):
    action = propose_chapati(client, fake_llm)
    assert action["action_type"] == "save_recipe"
    assert action["payload"]["per_ref"]["calories"] == 97.5            # (346 + 44) / 4
    assert client.get("/api/foods").json() == []

    assert client.post(f"/api/actions/{action['id']}/confirm").status_code == 200
    foods = foods_by_name(client)
    recipe = foods["Chapati"]
    assert recipe["kind"] == "recipe" and recipe["measures"] == "per 1 piece"
    assert [i["name"] for i in recipe["ingredients"]] == ["multigrain atta", "sunflower oil"]
    assert foods["multigrain atta"]["brand_name"] == "Pillsbury"


def test_logging_with_a_recipe(client, user, fake_llm):
    client.post(f"/api/actions/{propose_chapati(client, fake_llm)['id']}/confirm")
    recipe_id = foods_by_name(client)["Chapati"]["id"]
    action = chat_propose(client, fake_llm, "propose_entry", {
        "summary": "3 chapatis", "eaten_at": None, "meal_type": None,
        "items": [library_item(recipe_id, 3, "pieces", name="roti")],
    })
    item = action["payload"]["items"][0]
    assert item["source"] == "recipe" and item["ingredient_name"] == "Chapati"
    assert item["calories"] == 292.5


def test_recipe_without_yield_goes_back_to_the_model(client, user, fake_llm):
    from tests.conftest import text_reply
    provider = fake_llm(
        tool_reply("propose_recipe", {"name": "Dal", "ingredients": [ATTA], "yield_pieces": None,
                                      "yield_servings": None, "cooked_weight_g": None, "note": ""}),
        text_reply("How many servings does it make?"),
    )
    client.post("/api/chat", json={"message": "save my dal"})
    result = provider.calls[1]["messages"][-1]["content"][0]
    assert result["is_error"] and "needs a yield" in result["content"]


def test_updating_a_recipe_keeps_past_logs(client, user, fake_llm):
    client.post(f"/api/actions/{propose_chapati(client, fake_llm)['id']}/confirm")
    recipe_id = foods_by_name(client)["Chapati"]["id"]
    log = chat_propose(client, fake_llm, "propose_entry", {
        "summary": "2 chapatis", "eaten_at": None, "meal_type": None,
        "items": [library_item(recipe_id, 2, "piece")],
    })
    client.post(f"/api/actions/{log['id']}/confirm")
    before = client.get("/api/dashboard/daily").json()["consumed"]["calories"]

    more_oil = {**OIL, "quantity": 10, "calories": 88, "fat_g": 10}
    update = propose_chapati(client, fake_llm, oil=more_oil)
    assert update["payload"]["summary"] == "Update recipe: Chapati"
    client.post(f"/api/actions/{update['id']}/confirm")

    assert foods_by_name(client)["Chapati"]["calories"] == 108.5       # (346 + 88) / 4
    assert client.get("/api/dashboard/daily").json()["consumed"]["calories"] == before


def test_estimate_named_like_a_recipe_does_not_overwrite_it(client, user, fake_llm):
    client.post(f"/api/actions/{propose_chapati(client, fake_llm)['id']}/confirm")
    log_and_confirm(client, fake_llm, [{**CHICKEN, "ingredient_name": "chapati", "quantity": 1, "unit": "piece",
                                        "calories": 120, "protein_g": 3, "carbs_g": 20, "fat_g": 3}])
    recipe = foods_by_name(client)["Chapati"]
    assert recipe["kind"] == "recipe" and recipe["calories"] == 97.5


def test_ingredient_in_use_cannot_be_deleted_until_recipe_is(client, user, fake_llm):
    client.post(f"/api/actions/{propose_chapati(client, fake_llm)['id']}/confirm")
    foods = foods_by_name(client)
    r = client.delete(f"/api/foods/{foods['multigrain atta']['id']}")
    assert r.status_code == 409 and "Chapati" in r.json()["detail"]
    assert client.delete(f"/api/foods/{foods['Chapati']['id']}").status_code == 200
    assert client.delete(f"/api/foods/{foods['multigrain atta']['id']}").status_code == 200


def test_library_is_listed_in_llm_context(client, user, fake_llm):
    """Only saved foods named in the message are sent, which keeps prompts small."""
    log_and_confirm(client, fake_llm, [CHICKEN])
    from tests.conftest import text_reply
    provider = fake_llm(text_reply("Hi!"), text_reply("Which part?"))
    client.post("/api/chat", json={"message": "hi"})
    assert "chicken breast" not in provider.calls[0]["system_dynamic"].split('"my_foods"')[1]
    client.post("/api/chat", json={"message": "had some chicken with rice"})
    assert "chicken breast, cooked | per 100 g" in provider.calls[1]["system_dynamic"]


def test_other_users_foods_are_invisible(client, user, fake_llm):
    from tests.conftest import make_user
    log_and_confirm(client, fake_llm, [CHICKEN])
    food_id = foods_by_name(client)["chicken breast, cooked"]["id"]
    client.post("/api/auth/logout")
    make_user(client, "other@example.com")
    assert client.get("/api/foods").json() == []
    assert client.get(f"/api/foods/{food_id}").status_code == 404
