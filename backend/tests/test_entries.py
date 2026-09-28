"""Move / copy / edit / delete of logged food (chat + dashboard), progress card, and Stop."""
import pytest

from app.services import cancel
from app.services.progress import motivation
from tests.conftest import make_user, text_reply, tool_reply
from tests.test_foods import CHICKEN, OIL, chat_propose, log_and_confirm


def day(client):
    return client.get("/api/dashboard/daily").json()


def logged_entry(client, fake_llm, items=(CHICKEN, OIL)):
    log_and_confirm(client, fake_llm, list(items))
    return day(client)["entries"][-1]


# --- dashboard actions -------------------------------------------------------------

def test_move_one_item_splits_the_entry(client, user, fake_llm):
    entry = logged_entry(client, fake_llm)
    oil = entry["items"][1]
    before = day(client)["consumed"]["calories"]
    r = client.post(f"/api/entries/items/{oil['id']}/transfer", json={"to_meal_type": "dinner", "mode": "move"})
    assert r.status_code == 200
    d = day(client)
    meals = {e["meal_type"]: [i["ingredient_name"] for i in e["items"]] for e in d["entries"]}
    assert meals["dinner"] == ["sunflower oil"] and "chicken breast, cooked" in meals[entry["meal_type"]]
    assert d["consumed"]["calories"] == before          # nothing lost or duplicated


def test_moving_the_only_item_moves_the_entry(client, user, fake_llm):
    entry = logged_entry(client, fake_llm, [CHICKEN])
    client.post(f"/api/entries/items/{entry['items'][0]['id']}/transfer", json={"to_meal_type": "breakfast"})
    entries = day(client)["entries"]
    assert len(entries) == 1 and entries[0]["id"] == entry["id"] and entries[0]["meal_type"] == "breakfast"


def test_copy_duplicates_and_future_dates_are_refused(client, user, fake_llm):
    entry = logged_entry(client, fake_llm, [CHICKEN])
    item_id = entry["items"][0]["id"]
    client.post(f"/api/entries/items/{item_id}/transfer", json={"to_meal_type": "dinner", "mode": "copy"})
    assert day(client)["consumed"]["calories"] == 330
    r = client.post(f"/api/entries/items/{item_id}/transfer",
                    json={"to_meal_type": "dinner", "mode": "copy", "to_date": "2999-01-01"})
    assert r.status_code == 422


def test_change_quantity_scales_nutrients(client, user, fake_llm):
    entry = logged_entry(client, fake_llm, [CHICKEN])
    client.patch(f"/api/entries/items/{entry['items'][0]['id']}", json={"quantity": 150})
    item = day(client)["entries"][0]["items"][0]
    assert (item["quantity"], item["calories"], item["protein_g"]) == (150, 247.5, 46.5)


def test_deleting_last_item_removes_entry_and_macbro_is_told(client, user, fake_llm):
    entry = logged_entry(client, fake_llm, [CHICKEN])
    client.delete(f"/api/entries/items/{entry['items'][0]['id']}")
    assert day(client)["entries"] == []
    events = [m["content"] for m in client.get("/api/chat/history").json() if m["role"] == "event"]
    assert any("On the dashboard the user deleted" in e for e in events)


def test_cannot_touch_another_users_food(client, user, fake_llm):
    entry = logged_entry(client, fake_llm, [CHICKEN])
    client.post("/api/auth/logout")
    make_user(client, "other@example.com")
    item_id = entry["items"][0]["id"]
    assert client.delete(f"/api/entries/items/{item_id}").status_code == 404
    assert client.patch(f"/api/entries/items/{item_id}", json={"quantity": 1}).status_code == 404


# --- chat move ---------------------------------------------------------------------

def test_chat_move_is_one_confirmed_step(client, user, fake_llm):
    entry = logged_entry(client, fake_llm, [CHICKEN])
    action = chat_propose(client, fake_llm, "propose_move", {
        "entry_id": entry["id"], "item_ids": None, "to_meal_type": "breakfast", "to_date": None,
        "mode": "move", "summary": "Move to breakfast"}, message="move my snack to breakfast")
    assert action["action_type"] == "move"
    assert day(client)["entries"][0]["meal_type"] == entry["meal_type"]      # unchanged until confirmed
    client.post(f"/api/actions/{action['id']}/confirm")
    d = day(client)
    assert [e["meal_type"] for e in d["entries"]] == ["breakfast"] and d["consumed"]["calories"] == 165


def test_chat_partial_copy(client, user, fake_llm):
    entry = logged_entry(client, fake_llm)
    oil_id = entry["items"][1]["id"]
    action = chat_propose(client, fake_llm, "propose_move", {
        "entry_id": entry["id"], "item_ids": [oil_id], "to_meal_type": "dinner", "to_date": None,
        "mode": "copy", "summary": "Copy oil to dinner"})
    client.post(f"/api/actions/{action['id']}/confirm")
    assert day(client)["consumed"]["calories"] == 165 + 44 + 44     # oil copied, not moved


def test_delete_when_user_said_move_goes_back_to_model(client, user, fake_llm):
    entry = logged_entry(client, fake_llm, [CHICKEN])
    provider = fake_llm(tool_reply("propose_delete", {"entry_id": entry["id"], "summary": "x", "note": ""}),
                        text_reply("Let me move it instead."))
    client.post("/api/chat", json={"message": "move the evening snack to breakfast"})
    result = provider.calls[1]["messages"][-1]["content"][0]
    assert result["is_error"] and "propose_move" in result["content"]


# --- progress card -----------------------------------------------------------------

@pytest.mark.parametrize("kcal,protein,expect", [
    (120, 60, "past your calorie budget"),
    (95, 100, "perfect day"),
    (60, 80, "g protein to go"),
    (50, 52, "52% of your protein done, 48% to go"),
    (30, 30, "Good progress"),
    (5, 5, "just the start of your day"),
])
def test_motivation_messages(kcal, protein, expect):
    assert expect in motivation(kcal, protein, 40)


def test_confirm_posts_day_so_far_card(client, user, fake_llm):
    action = chat_propose(client, fake_llm, "propose_entry", {
        "summary": "m", "eaten_at": None, "meal_type": None, "items": [CHICKEN]})
    progress = client.post(f"/api/actions/{action['id']}/confirm").json()["progress"]
    assert progress["kind"] == "progress"
    assert progress["data"]["calories"]["consumed"] == 165
    assert progress["data"]["macros"][0]["label"] == "Protein"
    assert "Day so far" in progress["content"]
    assert client.get("/api/chat/history").json()[-1]["kind"] == "progress"


def test_rejecting_posts_no_card(client, user, fake_llm):
    action = chat_propose(client, fake_llm, "propose_entry", {
        "summary": "m", "eaten_at": None, "meal_type": None, "items": [CHICKEN]})
    assert client.post(f"/api/actions/{action['id']}/reject").json().get("progress") is None


# --- Stop / cancel -----------------------------------------------------------------

def test_cancel_registry_race_rules():
    cancel.start(1, "a")
    assert cancel.cancel(1, "a") == "cancelled"
    with pytest.raises(cancel.ChatCancelled):
        cancel.finish_or_cancelled(1, "a")
    cancel.start(1, "b")
    cancel.finish_or_cancelled(1, "b")
    assert cancel.cancel(1, "b") == "finished"           # too late: the reply was saved
    assert cancel.cancel(1, "early") == "cancelled"      # Stop arrived before the request
    cancel.start(1, "early")
    with pytest.raises(cancel.ChatCancelled):
        cancel.raise_if_cancelled(1, "early")


def test_stopped_turn_saves_nothing(client, user, fake_llm):
    from app.llm.provider import set_provider
    me = client.get("/api/auth/me").json()

    class StopsMidway:
        def complete(self, **_):
            cancel.cancel(me["id"], "req-1")       # user clicks Stop while the model is working
            return tool_reply("propose_entry", {"summary": "m", "eaten_at": None, "meal_type": None,
                                                "note": "", "items": [CHICKEN]})

    set_provider(StopsMidway())
    r = client.post("/api/chat", json={"message": "had chicken", "client_request_id": "req-1"})
    assert r.status_code == 409 and r.json()["detail"] == "cancelled"
    assert client.get("/api/chat/history").json() == []
    set_provider(None)
