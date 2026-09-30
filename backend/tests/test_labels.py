"""Branded foods: pack labels from Open Food Facts (stubbed, never the real service),
the label check in My Foods, and correcting past logs with the label's numbers."""
import pytest
from sqlalchemy import select

from app.db import SessionLocal
from app.models import LogEntryItem, User
from app.services import foods as foods_svc, labels
from tests.conftest import internal_id
from tests.test_foods import foods_by_name, log_and_confirm

BUTTER_ESTIMATE = {
    "ingredient_name": "butter", "brand_name": "Amul", "quantity": 10, "unit": "g",
    "calories": 70, "protein_g": 0, "carbs_g": 0, "fat_g": 7.8, "fiber_g": 0,
    "food_id": None, "unit_weight_g": None,
}

AMUL_BUTTER = {   # as Open Food Facts returns it
    "code": "8901262010016", "product_name": "Pasteurised Butter", "brands": "Amul, Amul India",
    "quantity": "100 g", "serving_size": "10 g", "serving_quantity": 10,
    "countries_tags": ["en:india"],
    "nutriments": {"energy-kcal_100g": 722, "proteins_100g": 0.5, "carbohydrates_100g": 0.1,
                   "fat_100g": 80, "sodium_100g": 0.4, "calcium_100g": 0.015},
}
FOREIGN_BUTTER = {**AMUL_BUTTER, "code": "5000000000001", "brands": "Lurpak", "countries_tags": ["en:denmark"]}
NO_MACROS = {**AMUL_BUTTER, "code": "8900000000002", "nutriments": {"energy-kcal_100g": 700}}


@pytest.fixture
def off(monkeypatch):
    """Stand-in for Open Food Facts: records the requests, answers from `products`."""
    calls = []
    products = {p["code"]: p for p in (AMUL_BUTTER, FOREIGN_BUTTER, NO_MACROS)}

    def fake_get(url, params=None):
        calls.append((url, params))
        if url == labels.SEARCH_URL:
            return {"products": [FOREIGN_BUTTER, NO_MACROS, AMUL_BUTTER]}
        code = url.rsplit("/", 1)[-1].removesuffix(".json")
        return {"status": 1, "product": products[code]} if code in products else {"status": 0}

    monkeypatch.setattr(labels, "_get", fake_get)
    return calls


def test_label_values_are_converted_to_our_units():
    lab = labels.product_to_label(AMUL_BUTTER)
    assert (lab["calories"], lab["fat_g"], lab["brand"], lab["grams_per_serving"]) == (722, 80, "Amul", 10)
    assert lab["micronutrients"] == {"calcium_mg": 15.0, "sodium_mg": 400.0}   # grams -> mg
    assert (lab["ref_qty"], lab["ref_unit"]) == (100, "g")


def test_drinks_are_per_100_ml_and_kilojoules_are_converted():
    lab = labels.product_to_label({**AMUL_BUTTER, "quantity": "200 ml",
                                   "nutriments": {"energy-kj_100g": 418.4, "proteins_100g": 3,
                                                  "carbohydrates_100g": 5, "fat_100g": 3}})
    assert lab["ref_unit"] == "ml" and lab["calories"] == 100


def test_a_label_missing_a_macro_is_not_offered():
    assert labels.product_to_label(NO_MACROS) is None


def test_search_puts_products_sold_in_india_first(client, user, off):
    r = client.get("/api/foods/label-search", params={"q": "amul butter"})
    assert r.status_code == 200, r.text
    assert [p["brand"] for p in r.json()] == ["Amul", "Lurpak"]      # the incomplete label is left out
    assert off[0][1]["search_terms"] == "amul butter"


def test_search_by_barcode(client, user, off):
    r = client.get("/api/foods/label-search", params={"q": "8901262010016"})
    assert [p["code"] for p in r.json()] == ["8901262010016"]
    assert client.get("/api/foods/label-search", params={"q": "8999999999999"}).json() == []


def test_open_food_facts_down_is_a_clear_error(client, user, monkeypatch):
    def down(url, params=None):
        raise labels.LabelLookupError("Open Food Facts didn't answer.")
    monkeypatch.setattr(labels, "_get", down)
    r = client.get("/api/foods/label-search", params={"q": "amul butter"})
    assert r.status_code == 502 and "Open Food Facts" in r.json()["detail"]


def test_branded_estimate_is_saved_unchecked(client, user, fake_llm):
    log_and_confirm(client, fake_llm, [BUTTER_ESTIMATE])
    butter = foods_by_name(client)["butter"]
    assert butter["brand_name"] == "Amul" and butter["label_checked"] is False
    assert butter["source"] == "estimate"


def test_using_a_label_replaces_the_numbers_and_corrects_past_logs(client, user, fake_llm, off):
    log_and_confirm(client, fake_llm, [BUTTER_ESTIMATE])
    butter = foods_by_name(client)["butter"]

    r = client.post(f"/api/foods/{butter['id']}/label", json={"code": "8901262010016"})
    assert r.status_code == 200, r.text
    food = r.json()
    assert (food["calories"], food["fat_g"], food["source"], food["label_checked"]) == (722, 80, "label", True)
    assert food["off_code"] == "8901262010016" and food["grams_per_serving"] == 10
    assert food["logs_corrected"] == 1

    with SessionLocal() as db:   # day totals are computed from the items, so they follow
        logged = db.scalars(select(LogEntryItem)).one()
        assert (logged.calories, logged.fat_g, logged.source) == (72.2, 8.0, "library")
        assert logged.micronutrients == {"sodium_mg": 40.0, "calcium_mg": 1.5}


def test_past_logs_are_left_alone_when_asked(client, user, fake_llm, off):
    log_and_confirm(client, fake_llm, [BUTTER_ESTIMATE])
    butter = foods_by_name(client)["butter"]
    r = client.post(f"/api/foods/{butter['id']}/label", json={"code": "8901262010016", "correct_logs": False})
    assert r.json()["logs_corrected"] == 0


def test_the_label_is_fetched_again_not_taken_from_the_browser(client, user, fake_llm, off):
    log_and_confirm(client, fake_llm, [BUTTER_ESTIMATE])
    butter = foods_by_name(client)["butter"]
    r = client.post(f"/api/foods/{butter['id']}/label", json={"code": "8901262010016", "calories": 1})
    assert r.json()["calories"] == 722
    assert off[-1][0].endswith("/8901262010016.json")
    assert client.post(f"/api/foods/{butter['id']}/label", json={"code": "8900000000002"}).status_code == 502


def test_a_later_estimate_never_overwrites_the_label(client, user, fake_llm, off):
    log_and_confirm(client, fake_llm, [BUTTER_ESTIMATE])
    butter = foods_by_name(client)["butter"]
    client.post(f"/api/foods/{butter['id']}/label", json={"code": "8901262010016"})
    log_and_confirm(client, fake_llm, [{**BUTTER_ESTIMATE, "calories": 60, "fat_g": 6.7}])
    assert foods_by_name(client)["butter"]["calories"] == 722


def test_typing_the_label_in_by_hand(client, user, fake_llm):
    log_and_confirm(client, fake_llm, [BUTTER_ESTIMATE])
    butter = foods_by_name(client)["butter"]
    body = {"name": "butter", "brand_name": "Amul", "ref_qty": 100, "ref_unit": "g", "calories": 722,
            "protein_g": 0.5, "carbs_g": 0.1, "fat_g": 80, "label_checked": True, "correct_logs": True}
    r = client.put(f"/api/foods/{butter['id']}", json=body)
    assert r.status_code == 200, r.text
    assert (r.json()["source"], r.json()["label_checked"], r.json()["logs_corrected"]) == ("label", True, 1)

    r = client.put(f"/api/foods/{butter['id']}", json={**body, "label_checked": False, "correct_logs": False})
    assert (r.json()["source"], r.json()["label_checked"], r.json()["logs_corrected"]) == ("user", False, 0)


def test_brand_and_name_together_find_the_saved_food(client, user, fake_llm):
    log_and_confirm(client, fake_llm, [BUTTER_ESTIMATE])
    uid = internal_id(client.get("/api/auth/me").json()["id"])
    with SessionLocal() as db:
        assert foods_svc.match_saved(db, uid, "amul butter").name == "butter"
        assert foods_svc.match_saved(db, uid, "butter").name == "butter"


def test_label_foods_are_marked_for_the_model(client, user, fake_llm, off):
    log_and_confirm(client, fake_llm, [BUTTER_ESTIMATE])
    butter = foods_by_name(client)["butter"]
    client.post(f"/api/foods/{butter['id']}/label", json={"code": "8901262010016"})
    uid = internal_id(client.get("/api/auth/me").json()["id"])
    with SessionLocal() as db:
        line = foods_svc.library_context(db, db.get(User, uid))[0]
    assert "butter (Amul)" in line and "| label |" in line


def test_brand_and_name_in_chat_use_the_label_without_the_ai(client, user, fake_llm, off):
    log_and_confirm(client, fake_llm, [BUTTER_ESTIMATE])
    butter = foods_by_name(client)["butter"]
    client.post(f"/api/foods/{butter['id']}/label", json={"code": "8901262010016"})
    fake_llm()   # no model replies scripted: the fast path must answer
    r = client.post("/api/chat", json={"message": "10 g amul butter"})
    assert r.status_code == 200, r.text
    item = r.json()[-1]["actions"][0]["payload"]["items"][0]
    assert (item["food_id"], item["calories"]) == (butter["id"], 72.2)
