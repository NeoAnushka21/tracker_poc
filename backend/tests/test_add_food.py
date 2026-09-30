"""Saved Food → + Add: a generic food, a branded product (typed or picked on Open Food Facts)
and a recipe, all typed in by the user without the AI."""
from tests.test_foods import foods_by_name
from tests.test_labels import off  # noqa: F401  (fixture: Open Food Facts stubbed)

PANEER = {"name": "paneer", "brand_name": None, "ref_qty": 100, "ref_unit": "g", "calories": 265,
          "protein_g": 18.3, "carbs_g": 1.2, "fat_g": 20.8, "fiber_g": 0,
          "grams_per_piece": None, "grams_per_serving": None, "micronutrients": {"calcium_mg": 480}}


def test_add_a_generic_food(client, user):
    r = client.post("/api/foods", json=PANEER)
    assert r.status_code == 201, r.text
    food = r.json()
    assert (food["kind"], food["source"], food["label_checked"], food["brand_name"]) == ("food", "user", False, None)
    assert food["micronutrients"] == {"calcium_mg": 480}
    assert client.post("/api/foods", json=PANEER).status_code == 409      # same name again


def test_add_a_branded_product_from_the_pack(client, user):
    body = {**PANEER, "brand_name": "Amul", "label_checked": True, "grams_per_serving": 50}
    food = client.post("/api/foods", json=body).json()
    assert (food["brand_name"], food["source"], food["label_checked"], food["off_code"]) == ("Amul", "label", True, None)
    # a plain "paneer" and "paneer · Amul" are different foods
    assert client.post("/api/foods", json=PANEER).status_code == 201


def test_add_a_branded_product_picked_on_open_food_facts(client, user, off):
    body = {**PANEER, "name": "butter", "brand_name": "Amul", "calories": 1, "label_checked": True,
            "label_code": "8901262010016"}
    food = client.post("/api/foods", json=body).json()
    assert (food["calories"], food["fat_g"], food["off_code"], food["grams_per_serving"]) == (722, 80, "8901262010016", 10)
    assert off[-1][0].endswith("/8901262010016.json")      # fetched again, the typed calories are ignored


def recipe(ingredients, **yields) -> dict:
    return {"name": "Paneer bhurji", "ingredients": ingredients, **yields}


def test_recipe_from_saved_and_general_foods(client, user):
    paneer_id = client.post("/api/foods", json=PANEER).json()["id"]
    body = recipe([{"name": "paneer", "food_id": paneer_id, "quantity": 200, "unit": "g"},
                   {"name": "ghee", "quantity": 1, "unit": "tbsp"}], yield_servings=2)

    preview = client.post("/api/foods/recipes/preview", json=body)
    assert preview.status_code == 200, preview.text
    p = preview.json()
    assert (p["ref_qty"], p["ref_unit"]) == (1, "serving")
    assert [i["from"] for i in p["ingredients"]] == ["library", "general"]
    assert len(client.get("/api/foods").json()) == 1                        # preview saved nothing

    r = client.post("/api/foods/recipes", json=body)
    assert r.status_code == 201, r.text
    saved = r.json()
    assert saved["kind"] == "recipe" and abs(saved["calories"] - p["per_ref"]["calories"]) < 0.1
    assert [i["name"] for i in saved["ingredients"]] == ["paneer", "ghee"]
    assert "ghee" in foods_by_name(client)                                  # general-list food learned
    assert client.post("/api/foods/recipes", json=body).status_code == 409


def test_recipe_problems_are_explained(client, user):
    def err(body):
        r = client.post("/api/foods/recipes/preview", json=body)
        assert r.status_code == 422, r.text
        return r.json()["detail"]

    assert "isn't in Saved Food" in err(recipe([{"name": "dragonfruit jam", "quantity": 10, "unit": "g"}], yield_servings=1))
    assert "raw or cooked" in err(recipe([{"name": "rice", "quantity": 100, "unit": "g"}], yield_servings=1))
    assert "yield" in err(recipe([{"name": "banana", "quantity": 100, "unit": "g"}]))
    client.post("/api/foods", json=PANEER)
    assert "can't be measured in 'piece'" in err(recipe([{"name": "paneer", "quantity": 2, "unit": "piece"}], yield_servings=1))
