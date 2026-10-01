"""Branded items on a chat card: the pack label is found first (Open Food Facts, stubbed, never the
real service), the user picks the product on the card, the AI's estimate is the fallback."""
import pytest
from sqlalchemy import select

from app.db import SessionLocal
from app.models import LogEntryItem
from app.services import label_match, labels
from tests.conftest import tool_reply
from tests.test_dashboard_add import add, estimate_reply
from tests.test_foods import chat_propose, foods_by_name
from tests.test_labels import AMUL_BUTTER, BUTTER_ESTIMATE, FOREIGN_BUTTER, NO_MACROS

GARLIC_BUTTER = {**AMUL_BUTTER, "code": "8901262010023", "product_name": "Garlic Butter",
                 "nutriments": {**AMUL_BUTTER["nutriments"], "energy-kcal_100g": 690, "fat_100g": 75}}
BREAD = {   # sliced bread: a serving on the label, pieces weighed by the AI
    "code": "8901725121112", "product_name": "Multigrain Bread", "brands": "Modern",
    "quantity": "400 g", "serving_size": "2 slices (50 g)", "serving_quantity": 50, "countries_tags": ["en:india"],
    "nutriments": {"energy-kcal_100g": 250, "proteins_100g": 9, "carbohydrates_100g": 45, "fat_100g": 3.5,
                   "fiber_100g": 6},
}
BREAD_ESTIMATE = {
    "ingredient_name": "multigrain bread", "brand_name": "Modern", "quantity": 2, "unit": "piece",
    "calories": 130, "protein_g": 4.5, "carbs_g": 23, "fat_g": 2, "fiber_g": 3,
    "food_id": None, "unit_weight_g": 27,
}


@pytest.fixture
def off(monkeypatch):
    """Open Food Facts stand-in: `found` is what a search returns; `calls` records requests."""
    state = {"found": [FOREIGN_BUTTER, NO_MACROS, AMUL_BUTTER], "calls": [], "down": False}
    products = {p["code"]: p for p in (AMUL_BUTTER, GARLIC_BUTTER, FOREIGN_BUTTER, BREAD)}

    def fake_get(url, params=None, timeout=None):
        state["calls"].append(url)
        if state["down"]:
            raise labels.LabelLookupError("Open Food Facts didn't answer.")
        if url == labels.SEARCH_URL:
            return {"products": state["found"]}
        code = url.rsplit("/", 1)[-1].removesuffix(".json")
        return {"status": 1, "product": products[code]} if code in products else {"status": 0}

    monkeypatch.setattr(labels, "_get", fake_get)
    return state


def propose(client, fake_llm, *items, message="10 g amul butter"):
    return chat_propose(client, fake_llm, "propose_entry",
                        {"summary": "meal", "eaten_at": None, "meal_type": None, "items": list(items)}, message)


def pick(client, action, index=0, code=None):
    return client.post(f"/api/actions/{action['id']}/items/{index}/label", json={"code": code})


# --- matching ---------------------------------------------------------------------------

def test_one_clear_product_is_offered_alone(client, user, fake_llm, off):
    action = propose(client, fake_llm, BUTTER_ESTIMATE)
    item = action["payload"]["items"][0]
    match = item["label_match"]
    assert match["status"] == "sure" and match["picked"] is None
    assert [o["code"] for o in match["options"]] == ["8901262010016"]   # Lurpak (another brand) and the incomplete label left out
    assert item["calories"] == 70 and item["source"] == "estimate"     # nothing applied before the tap


def test_similar_products_with_other_numbers_are_choices(client, user, fake_llm, off):
    off["found"] = [AMUL_BUTTER, GARLIC_BUTTER]
    match = propose(client, fake_llm, BUTTER_ESTIMATE)["payload"]["items"][0]["label_match"]
    assert match["status"] == "choose"
    assert [o["code"] for o in match["options"]] == ["8901262010016", "8901262010023"]


def test_the_same_label_in_another_pack_size_is_shown_once(client, user, fake_llm, off):
    off["found"] = [AMUL_BUTTER, {**AMUL_BUTTER, "code": "8901262010030", "quantity": "500 g"}]
    match = propose(client, fake_llm, BUTTER_ESTIMATE)["payload"]["items"][0]["label_match"]
    assert match["status"] == "sure" and len(match["options"]) == 1


def test_nothing_found_keeps_the_estimate(client, user, fake_llm, off):
    off["found"] = [FOREIGN_BUTTER]
    item = propose(client, fake_llm, BUTTER_ESTIMATE)["payload"]["items"][0]
    assert item["label_match"]["status"] == "none" and item["calories"] == 70


def test_unbranded_and_saved_foods_are_not_looked_up(client, user, fake_llm, off):
    item = propose(client, fake_llm, {**BUTTER_ESTIMATE, "brand_name": None})["payload"]["items"][0]
    assert "label_match" not in item and off["calls"] == []


def test_typos_and_joined_words_still_match():
    lab = labels.product_to_label({**AMUL_BUTTER, "product_name": "NutriChoice Digestive", "brands": "Britannia"})
    s = label_match.score(lab, "Britania", "nutri choice digestive biscuits")
    assert s["brand_ok"] and s["coverage"] == 0.75     # "biscuits" isn't in the pack name
    assert label_match.score(lab, "Parle", "digestive")["brand_ok"] is False


def test_open_food_facts_down_then_find_the_label(client, user, fake_llm, off):
    off["down"] = True
    action = propose(client, fake_llm, BUTTER_ESTIMATE)
    assert action["payload"]["items"][0]["label_match"]["status"] == "unavailable"
    off["down"] = False
    r = client.post(f"/api/actions/{action['id']}/items/0/label-search")
    assert r.status_code == 200, r.text
    assert r.json()["payload"]["items"][0]["label_match"]["status"] == "sure"


def test_searches_are_cached(client, user, fake_llm, off):
    propose(client, fake_llm, BUTTER_ESTIMATE)
    propose(client, fake_llm, BUTTER_ESTIMATE)
    assert off["calls"].count(labels.SEARCH_URL) == 1


def test_dashboard_estimates_have_no_label_choices(client, user, fake_llm, off):
    fake_llm(estimate_reply([{**BUTTER_ESTIMATE, "micronutrients": None}]))
    r = add(client, name="amul butter", quantity=10)
    assert "label_match" not in r.json()["action"]["payload"]["items"][0]


# --- the user's tap ---------------------------------------------------------------------

def test_picking_the_product_uses_its_label_and_confirming_marks_it_checked(client, user, fake_llm, off):
    action = propose(client, fake_llm, BUTTER_ESTIMATE)
    r = pick(client, action, code="8901262010016")
    assert r.status_code == 200, r.text
    p = r.json()["payload"]
    item = p["items"][0]
    assert (item["calories"], item["fat_g"], item["source"], item["off_code"]) == (72.2, 8.0, "label", "8901262010016")
    assert item["label_match"]["picked"] == "8901262010016" and item["weight_estimated"] is False
    assert p["totals"]["calories"] == 72.2
    assert foods_by_name(client) == {}                                  # still nothing saved

    assert client.post(f"/api/actions/{action['id']}/confirm").status_code == 200
    butter = foods_by_name(client)["butter"]
    assert (butter["label_checked"], butter["source"], butter["off_code"], butter["calories"]) == (True, "label", "8901262010016", 722)
    with SessionLocal() as db:
        logged = db.scalars(select(LogEntryItem)).one()
        assert (logged.calories, logged.source, logged.user_food_id) == (72.2, "label", butter["id"])


def test_none_of_these_puts_the_estimate_back(client, user, fake_llm, off):
    action = propose(client, fake_llm, BUTTER_ESTIMATE)
    pick(client, action, code="8901262010016")
    item = pick(client, action, code=None).json()["payload"]["items"][0]
    assert (item["calories"], item["source"], item["label_match"]["declined"]) == (70, "estimate", True)
    assert "off_code" not in item
    client.post(f"/api/actions/{action['id']}/confirm")
    assert foods_by_name(client)["butter"]["label_checked"] is False


def test_only_offered_products_can_be_picked(client, user, fake_llm, off):
    action = propose(client, fake_llm, BUTTER_ESTIMATE)
    assert pick(client, action, code="5000000000001").status_code == 422     # Lurpak wasn't offered
    assert pick(client, action, index=3, code="8901262010016").status_code == 422


def test_pieces_use_the_ai_weight_and_say_so(client, user, fake_llm, off):
    off["found"] = [BREAD]
    action = propose(client, fake_llm, BREAD_ESTIMATE, message="2 slices modern multigrain bread")
    item = pick(client, action, code="8901725121112").json()["payload"]["items"][0]
    assert item["calories"] == 135.0 and item["weight_estimated"] is True   # 2 x 27 g at 250 kcal / 100 g
    client.post(f"/api/actions/{action['id']}/confirm")
    bread = foods_by_name(client)["multigrain bread"]
    assert (bread["grams_per_piece"], bread["grams_per_serving"], bread["label_checked"]) == (27, 50, True)


def test_servings_use_the_label_serving(client, user, fake_llm, off):
    off["found"] = [BREAD]
    action = propose(client, fake_llm, {**BREAD_ESTIMATE, "unit": "serving", "quantity": 1, "unit_weight_g": None})
    item = pick(client, action, code="8901725121112").json()["payload"]["items"][0]
    assert item["calories"] == 125.0 and item["weight_estimated"] is False


def test_an_amount_that_cant_be_weighed_asks_for_grams(client, user, fake_llm, off):
    action = propose(client, fake_llm, {**BUTTER_ESTIMATE, "unit": "tbsp", "quantity": 1, "unit_weight_g": None})
    r = pick(client, action, code="8901262010016")
    assert r.status_code == 422 and "grams" in r.json()["detail"]


def test_someone_elses_card_cant_be_changed(client, user, fake_llm, off):
    action = propose(client, fake_llm, BUTTER_ESTIMATE)
    client.post("/api/auth/logout")
    from tests.conftest import make_user
    make_user(client, "other@example.com")
    assert pick(client, action, code="8901262010016").status_code == 404


def test_a_pick_carries_over_when_the_card_is_changed(client, user, fake_llm, off):
    action = propose(client, fake_llm, BUTTER_ESTIMATE)
    pick(client, action, code="8901262010016")
    fake_llm(tool_reply("propose_entry", {"note": "ok", "summary": "meal", "eaten_at": None, "meal_type": None,
                                          "items": [{**BUTTER_ESTIMATE, "quantity": 20, "calories": 140, "fat_g": 15.6}]}))
    r = client.post("/api/chat", json={"message": "make it 20 g", "feedback_on_action_id": action["id"]})
    item = r.json()[-1]["actions"][0]["payload"]["items"][0]
    assert (item["calories"], item["source"], item["label_match"]["how"]) == (144.4, "label", "picked")


# --- a barcode scanned in the chat -------------------------------------------------------

def test_a_scanned_barcode_comes_ready_on_the_card(client, user, fake_llm, off):
    off["found"] = []
    provider = fake_llm(tool_reply("propose_entry", {"note": "ok", "summary": "bread", "eaten_at": None, "meal_type": None,
                                                     "items": [BREAD_ESTIMATE]}))
    r = client.post("/api/chat", json={"message": "2 slices Modern Multigrain Bread", "barcode": "8901725121112"})
    assert r.status_code == 200, r.text
    sent = provider.calls[0]["messages"][0]["content"]
    assert sent.startswith("[Pack barcode scanned in the app: Multigrain Bread, brand Modern (400 g pack)]")
    item = r.json()[-1]["actions"][0]["payload"]["items"][0]
    assert (item["source"], item["off_code"], item["label_match"]["how"]) == ("label", "8901725121112", "barcode")
    assert r.json()[0]["data"]["barcode"] == "8901725121112"


def test_a_barcode_that_isnt_known_leaves_the_estimate(client, user, fake_llm, off):
    provider = fake_llm(tool_reply("propose_entry", {"note": "ok", "summary": "x", "eaten_at": None, "meal_type": None,
                                                     "items": [BUTTER_ESTIMATE]}))
    r = client.post("/api/chat", json={"message": "10 g amul butter", "barcode": "8999999999999"})
    assert "not on Open Food Facts" in provider.calls[0]["messages"][0]["content"]
    assert r.json()[-1]["actions"][0]["payload"]["items"][0]["source"] == "estimate"


def test_a_barcode_must_be_digits(client, user, fake_llm):
    assert client.post("/api/chat", json={"message": "x", "barcode": "abc"}).status_code == 422
