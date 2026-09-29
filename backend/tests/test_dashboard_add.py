"""Dashboard "Add food": saved foods are added directly; other foods get one AI estimate to confirm."""
from datetime import date, timedelta

from app.llm.provider import LLMError, set_provider
from tests.conftest import text_reply, tool_reply
from tests.test_foods import CHICKEN, chat_propose, foods_by_name, log_and_confirm

PANEER = {
    "ingredient_name": "paneer", "brand_name": None, "quantity": 100, "unit": "g",
    "calories": 265, "protein_g": 18, "carbs_g": 1.2, "fat_g": 21, "fiber_g": 0,
    "food_id": None, "unit_weight_g": None, "micronutrients": None,
}


def day(client, d: str | None = None):
    return client.get(f"/api/dashboard/daily{f'?day={d}' if d else ''}").json()


def add(client, **body):
    return client.post("/api/entries/add", json={"quantity": 100, "unit": "g", "meal_type": "dinner", **body})


def estimate_reply(items=(PANEER,), note="Plain paneer, about 100 g."):
    return tool_reply("propose_entry", {"summary": "Paneer", "eaten_at": None, "meal_type": None,
                                        "items": list(items), "note": note})


def meal_items(client, meal: str, d: str | None = None) -> list[dict]:
    return [i for e in day(client, d)["entries"] if e["meal_type"] == meal for i in e["items"]]


# --- saved foods: no AI ------------------------------------------------------------

def test_saved_food_is_added_directly_without_the_model(client, user, fake_llm):
    log_and_confirm(client, fake_llm, [CHICKEN])
    provider = fake_llm()                       # an empty script: any model call would fail
    r = add(client, name="Chicken Breast, Cooked", quantity=200)
    assert r.status_code == 200 and r.json()["status"] == "added"
    assert provider.calls == []
    [item] = meal_items(client, "dinner")
    assert item["calories"] == 330 and item["quantity"] == 200


def test_saved_food_by_id_and_unit_it_cannot_use(client, user, fake_llm):
    log_and_confirm(client, fake_llm, [CHICKEN])
    food_id = foods_by_name(client)["chicken breast, cooked"]["id"]
    assert foods_by_name(client)["chicken breast, cooked"]["units"] == ["g"]
    r = add(client, name="anything", food_id=food_id, quantity=1, unit="bowl")
    assert r.status_code == 422 and "Use: g" in r.json()["detail"]
    assert add(client, name="x", food_id=99999).status_code == 404


def test_added_food_joins_the_meal_and_its_time(client, user, fake_llm):
    log_and_confirm(client, fake_llm, [CHICKEN])
    entry = day(client)["entries"][0]
    fake_llm()
    add(client, name="chicken breast, cooked", meal_type=entry["meal_type"])
    entries = [e for e in day(client)["entries"] if e["meal_type"] == entry["meal_type"]]
    assert len(entries) == 2 and entries[1]["eaten_at"] == entry["eaten_at"]


def test_past_day_ok_future_day_refused(client, user, fake_llm):
    log_and_confirm(client, fake_llm, [CHICKEN])
    yesterday = (date.fromisoformat(day(client)["date"]) - timedelta(days=1)).isoformat()
    tomorrow = (date.fromisoformat(day(client)["date"]) + timedelta(days=1)).isoformat()
    assert add(client, name="chicken breast, cooked", day=yesterday, meal_type="breakfast").status_code == 200
    [item] = meal_items(client, "breakfast", yesterday)
    assert item["ingredient_name"] == "chicken breast, cooked"
    assert day(client, yesterday)["entries"][0]["eaten_at"] == f"{yesterday}T08:00"
    assert add(client, name="chicken breast, cooked", day=tomorrow).status_code == 422
    assert add(client, name="chicken breast, cooked", meal_type="brunch").status_code == 422


# --- new foods: AI estimate, then confirm -------------------------------------------

def test_new_food_is_estimated_and_saved_only_on_confirm(client, user, fake_llm):
    provider = fake_llm(estimate_reply())
    r = add(client, name="paneer", meal_type="lunch")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["status"] == "estimate" and body["note"] == "Plain paneer, about 100 g."
    action = body["action"]
    assert action["status"] == "pending" and action["payload"]["meal_type"] == "lunch"
    assert action["payload"]["origin"] == "dashboard"
    assert [t["name"] for t in provider.calls[0]["tools"]] == ["propose_entry"]
    assert day(client)["entries"] == [] and "paneer" not in foods_by_name(client)

    r = client.post(f"/api/actions/{action['id']}/confirm")
    assert r.status_code == 200 and r.json()["progress"] is None       # no card posted to the chat
    [item] = meal_items(client, "lunch")
    assert item["calories"] == 265
    assert foods_by_name(client)["paneer"]["calories"] == 265          # learned, like the chat
    chat = client.get("/api/chat/history").json()
    assert all(m["role"] == "event" for m in chat)                     # nothing visible in the chat


def test_estimate_is_not_a_chat_proposal(client, user, fake_llm):
    fake_llm(estimate_reply())
    action = add(client, name="paneer").json()["action"]
    # A chat proposal made meanwhile neither shows nor replaces the dashboard estimate.
    chat_propose(client, fake_llm, "propose_entry",
                 {"summary": "meal", "eaten_at": None, "meal_type": None, "items": [CHICKEN]})
    assert client.post(f"/api/actions/{action['id']}/confirm").status_code == 200


def test_discarded_estimate_saves_nothing(client, user, fake_llm):
    fake_llm(estimate_reply())
    action = add(client, name="paneer").json()["action"]
    assert client.post(f"/api/actions/{action['id']}/reject").status_code == 200
    assert day(client)["entries"] == [] and "paneer" not in foods_by_name(client)


def test_estimate_goes_through_the_energy_check(client, user, fake_llm):
    bad = {**PANEER, "calories": 100}
    provider = fake_llm(estimate_reply([bad]), estimate_reply())
    body = add(client, name="paneer").json()
    assert body["status"] == "estimate" and len(provider.calls) == 2
    assert "Calories and macros don't agree" in str(provider.calls[1]["messages"])


def test_not_a_food(client, user, fake_llm):
    fake_llm(text_reply("That doesn't look like a food or drink."))
    r = add(client, name="my keyboard")
    assert r.json() == {"status": "no_estimate", "message": "That doesn't look like a food or drink."}


def test_ai_down_gives_friendly_error(client, user, fake_llm):
    class Broken:
        def complete(self, **_):
            raise LLMError("down")

    set_provider(Broken())
    r = add(client, name="paneer")
    assert r.status_code == 503 and "temporarily down" in r.json()["detail"]
    assert day(client)["entries"] == []
