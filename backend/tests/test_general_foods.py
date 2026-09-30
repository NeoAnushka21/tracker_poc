"""The built-in general food list (USDA): first logs of common foods without the AI, and
"raw or cooked?" asked, never assumed."""
import pytest

from app.services import general_foods
from app.services.foods import _key
from tests.conftest import text_reply, tool_reply
from tests.test_dashboard_add import add, meal_items
from tests.test_foods import CHICKEN, foods_by_name, log_and_confirm
from tests.test_limits import allowance
from tests.test_routing import chat


def card(reply: dict) -> dict:
    [action] = reply["actions"]
    return action["payload"]


# --- the data ----------------------------------------------------------------------------

def test_list_is_sound():
    by_id, groups, index = general_foods._load()
    assert 250 <= len(by_id) <= 500
    for base, group in groups.items():
        assert set(group) in ({None}, {"raw", "cooked"}), base
        for e in group.values():
            assert e["calories"] > 0 or e["name"] in ("black coffee", "black tea", "vinegar"), e["name"]
            # Every name and alias finds its own food (no two foods share a name).
            for name in [base, *e["aliases"]]:
                assert index.get(_key(name)) == base, name
            # Calories agree with 4/4/9 macros (catches a food pointed at the wrong USDA row).
            # Skipped: alcohol (7 kcal/g) and cocoa powder (USDA uses low energy factors for it).
            macros = 4 * e["protein_g"] + 4 * e["carbs_g"] + 9 * e["fat_g"]
            if e["calories"] > 100 and e["name"] not in ("beer", "red wine", "whisky", "cocoa powder"):
                assert macros == pytest.approx(e["calories"], rel=0.2), e["name"]


def test_find_asks_raw_or_cooked_instead_of_assuming():
    assert general_foods.find("chicken breast").options == ["raw", "cooked"]
    assert general_foods.find("rice").entry is None                          # "rice" alone: ask
    assert general_foods.display_name(general_foods.find("boiled rice").entry) == "white rice, cooked"
    assert general_foods.display_name(general_foods.find("raw chiken brest").entry) == "chicken breast, raw"
    assert general_foods.find("kela").entry["name"] == "banana"               # Indian alias
    assert general_foods.find("boiled egg").entry["name"] == "boiled egg"     # a name with a state word
    for other in ("chicken curry", "fried rice", "paneer", "idlis"):          # dishes, missing foods, 'imli' typo
        assert general_foods.find(other) is None, other


# --- chat ----------------------------------------------------------------------------------

def test_common_food_logs_without_the_ai(client, user, fake_llm):
    no = fake_llm()                                                            # any model call would fail
    reply = chat(client, "had 150 g banana and 1 tbsp ghee for breakfast")
    p = card(reply)
    assert p["meal_type"] == "breakfast"
    assert [(i["ingredient_name"], i["source"]) for i in p["items"]] == [("banana", "general"), ("ghee", "general")]
    assert p["items"][0]["calories"] == 133.5                                  # 89 kcal per 100 g
    assert p["items"][1]["unit_weight_g"] == 12.8                              # USDA: 1 tbsp ghee = 12.8 g
    assert "general food list" in reply["content"]
    assert no.calls == [] and allowance(client)["used"] == 0


def test_raw_or_cooked_is_asked_then_logged(client, user, fake_llm):
    no = fake_llm()
    ask = chat(client, "200 g rice for lunch")
    assert ask["actions"] == [] and "raw or cooked" in ask["content"]
    assert ask["data"]["ask_state"]["items"] == ["rice"]
    p = card(chat(client, "cookd"))                                            # typo in the answer is fine
    assert p["meal_type"] == "lunch"
    [item] = p["items"]
    assert (item["ingredient_name"], item["calories"]) == ("white rice, cooked", 260)
    assert no.calls == []


def test_mixed_answer_for_two_foods(client, user, fake_llm):
    no = fake_llm()
    ask = chat(client, "200 g chicken breast and 100 g dal")
    assert "chicken breast, dal" in ask["content"]
    items = card(chat(client, "chicken raw, dal cooked"))["items"]
    assert [i["ingredient_name"] for i in items] == ["chicken breast, raw", "lentils, cooked"]
    assert no.calls == []


def test_an_unrelated_reply_isnt_taken_as_the_answer(client, user, fake_llm):
    fake_llm()
    chat(client, "200 g rice")
    llm = fake_llm(text_reply("Looking good!"))
    chat(client, "how are my macros looking this week overall?")               # not an answer: goes to the AI
    assert len(llm.calls) == 1


def test_counted_pieces_arent_asked(client, user, fake_llm):
    llm = fake_llm(tool_reply("propose_entry", {"summary": "x", "eaten_at": None, "meal_type": None,
                                                "items": [CHICKEN]}))
    chat(client, "2 chicken drumsticks")                                       # no weight: the AI handles it
    assert len(llm.calls) == 1


def test_confirmed_general_food_joins_saved_food(client, user, fake_llm):
    fake_llm()
    action = chat(client, "had 2 banana")["actions"][0]
    assert action["payload"]["items"][0]["quantity"] == 2
    client.post(f"/api/actions/{action['id']}/confirm")
    saved = foods_by_name(client)["banana"]
    assert saved["source"] == "general" and saved["calories"] == 89 and saved["grams_per_piece"] == 118
    item = card(chat(client, "had 1 banana"))["items"][0]                     # now from Saved Food
    assert item["source"] == "library" and item["calories"] == 105
    # Logging it again keeps one Saved Food entry and marks it as recently used.
    before = foods_by_name(client)["banana"]
    client.post(f"/api/actions/{chat(client, 'had 2 banana')['actions'][0]['id']}/confirm")
    after = [f for f in client.get("/api/foods").json() if f["name"] == "banana"]
    assert len(after) == 1 and after[0]["id"] == before["id"]


def test_saved_cooked_food_still_asks(client, user, fake_llm):
    log_and_confirm(client, fake_llm, [CHICKEN])                               # saved "chicken breast, cooked"
    fake_llm()
    assert "raw or cooked" in chat(client, "150 g chicken breast")["content"]
    item = card(chat(client, "150 g raw chicken breast"))["items"][0]          # not the saved cooked one
    assert item["ingredient_name"] == "chicken breast, raw" and item["source"] == "general"


# --- the AI path ------------------------------------------------------------------------------

def test_ai_can_point_at_a_general_food(client, user, fake_llm):
    item = {"ingredient_name": "banana", "brand_name": None, "quantity": 1, "unit": "bowl",
            "calories": 0, "protein_g": 0, "carbs_g": 0, "fat_g": 0, "fiber_g": 0, "food_id": None,
            "general_id": "banana", "unit_weight_g": 150, "micronutrients": None}
    llm = fake_llm(tool_reply("propose_entry", {"summary": "Banana", "eaten_at": None, "meal_type": None,
                                                "items": [item]}))
    got = card(chat(client, "a bowl of sliced banana with my coffee"))["items"][0]
    assert got["calories"] == 133.5 and got["source"] == "general"             # computed in code, not by the AI
    context = llm.calls[0]["system_dynamic"]
    assert "general_foods" in context and "banana |" in context


# --- Dashboard ----------------------------------------------------------------------------------

def test_dashboard_general_food_preview_and_state_question(client, user, fake_llm):
    no = fake_llm()
    r = add(client, name="banana", quantity=150, unit="g", meal_type="breakfast").json()
    assert r["status"] == "estimate" and r["source"] == "general"
    client.post(f"/api/actions/{r['action']['id']}/confirm")
    assert [i["ingredient_name"] for i in meal_items(client, "breakfast")] == ["banana"]
    assert foods_by_name(client)["banana"]["source"] == "general"             # kept in Saved Food too

    assert add(client, name="rice", quantity=200, unit="g", meal_type="lunch").json() == \
        {"status": "ask_state", "name": "white rice"}
    r = add(client, name="white rice, cooked", quantity=200, unit="g", meal_type="lunch").json()
    assert r["status"] == "estimate" and r["action"]["payload"]["totals"]["calories"] == 260
    assert no.calls == [] and allowance(client)["used"] == 0

