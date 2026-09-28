"""End-to-end API tests of the propose -> confirm loop, using a fake LLM."""
from datetime import timedelta

from app.db import SessionLocal
from app.models import PendingAction, utcnow
from tests.conftest import make_user, text_reply, tool_reply

CHICKEN = {
    "ingredient_name": "chicken breast, cooked", "brand_name": None, "quantity": 100, "unit": "g",
    "calories": 165, "protein_g": 31, "carbs_g": 0, "fat_g": 3.6, "fiber_g": 0,
}
CHICKEN_150 = {**CHICKEN, "quantity": 150, "calories": 248, "protein_g": 46.5, "fat_g": 5.4}
OIL = {
    "ingredient_name": "olive oil", "brand_name": None, "quantity": 10, "unit": "ml",
    "calories": 80, "protein_g": 0, "carbs_g": 0, "fat_g": 9.1, "fiber_g": 0,
}


def propose_meal(client, fake_llm, items=(CHICKEN, OIL), meal_type=None):
    fake_llm(
        tool_reply("propose_entry", {
            "summary": "Chicken with oil", "eaten_at": None, "meal_type": meal_type, "items": list(items),
        }),
        text_reply("Ready for you to confirm."),
    )
    r = client.post("/api/chat", json={"message": "had 100g cooked chicken, 10ml oil"})
    assert r.status_code == 200, r.text
    reply = r.json()[-1]
    assert reply["role"] == "assistant"
    assert len(reply["actions"]) == 1
    return reply["actions"][0]


def consumed_kcal(client):
    return client.get("/api/dashboard/daily").json()["consumed"]["calories"]


def test_onboarding_sets_targets(client, user):
    assert user["onboarded"] is True
    assert user["targets"]["calories"] > 0
    assert user["weight_kg"] == 80


def test_chat_requires_onboarding(client):
    client.post("/api/auth/register", json={"email": "new@example.com", "password": "password123"})
    assert client.post("/api/chat", json={"message": "hi"}).status_code == 409


def test_proposal_does_not_count_until_confirmed(client, user, fake_llm):
    action = propose_meal(client, fake_llm)
    assert action["status"] == "pending"
    assert action["payload"]["totals"]["calories"] == 245
    assert consumed_kcal(client) == 0        # pending never counts

    r = client.post(f"/api/actions/{action['id']}/confirm")
    assert r.status_code == 200, r.text
    assert r.json()["action"]["status"] == "confirmed"
    assert consumed_kcal(client) == 245

    # Can't confirm twice.
    assert client.post(f"/api/actions/{action['id']}/confirm").status_code == 409


def test_meal_type_explicit_overrides_inference(client, user, fake_llm):
    action = propose_meal(client, fake_llm, meal_type="breakfast")
    assert action["payload"]["meal_type"] == "breakfast"
    assert action["payload"]["meal_type_source"] == "stated"


def test_reject_saves_nothing(client, user, fake_llm):
    action = propose_meal(client, fake_llm)
    r = client.post(f"/api/actions/{action['id']}/reject")
    assert r.json()["action"]["status"] == "rejected"
    assert consumed_kcal(client) == 0


def test_new_proposal_supersedes_old_one(client, user, fake_llm):
    first = propose_meal(client, fake_llm)
    fake_llm(
        tool_reply("propose_entry", {
            "summary": "Chicken 150g", "eaten_at": None, "meal_type": None,
            "items": [CHICKEN_150],
        }),
        text_reply("Updated."),
    )
    r = client.post("/api/chat", json={"message": "it was 150g", "feedback_on_action_id": first["id"]})
    msgs = r.json()
    assert msgs[0]["role"] == "event"               # "Needs changes" note recorded
    second = msgs[-1]["actions"][0]
    assert client.post(f"/api/actions/{first['id']}/confirm").status_code == 409  # superseded
    assert client.post(f"/api/actions/{second['id']}/confirm").status_code == 200
    assert consumed_kcal(client) == 248


def test_edit_and_delete_go_through_confirmation(client, user, fake_llm):
    action = propose_meal(client, fake_llm)
    entry_id = client.post(f"/api/actions/{action['id']}/confirm").json()["action"]["result_entry_id"]

    fake_llm(
        tool_reply("propose_edit", {
            "entry_id": entry_id, "summary": "Chicken 100g -> 150g", "eaten_at": None, "meal_type": None,
            "items": [CHICKEN_150, OIL],
        }),
        text_reply("Here's the change."),
    )
    edit = client.post("/api/chat", json={"message": "chicken was 150g"}).json()[-1]["actions"][0]
    assert edit["payload"]["before"]["totals"]["calories"] == 245
    assert consumed_kcal(client) == 245             # unchanged until confirmed
    client.post(f"/api/actions/{edit['id']}/confirm")
    assert consumed_kcal(client) == 328

    fake_llm(
        tool_reply("propose_delete", {"entry_id": entry_id, "summary": "Delete chicken"}),
        text_reply("Delete this?"),
    )
    delete = client.post("/api/chat", json={"message": "delete that"}).json()[-1]["actions"][0]
    assert consumed_kcal(client) == 328
    client.post(f"/api/actions/{delete['id']}/confirm")
    assert consumed_kcal(client) == 0


def test_query_tool_sees_only_confirmed(client, user, fake_llm):
    action = propose_meal(client, fake_llm)
    client.post(f"/api/actions/{action['id']}/confirm")
    propose_meal(client, fake_llm)                 # second one left pending

    today = client.get("/api/dashboard/daily").json()["date"]
    provider = fake_llm(
        tool_reply("get_daily_summary", {"date": today}),
        text_reply("You had 245 kcal."),
    )
    client.post("/api/chat", json={"message": "what did I eat today?"})
    tool_result = provider.calls[1]["messages"][-1]["content"][0]
    assert tool_result["is_error"] is False
    assert '"calories": 245' in tool_result["content"]


def test_bad_tool_input_returns_error_to_llm(client, user, fake_llm):
    provider = fake_llm(
        tool_reply("propose_delete", {"entry_id": 9999, "summary": "x"}),
        text_reply("I couldn't find that entry."),
    )
    r = client.post("/api/chat", json={"message": "delete something"})
    assert r.status_code == 200
    tool_result = provider.calls[1]["messages"][-1]["content"][0]
    assert tool_result["is_error"] is True


def test_other_user_cannot_confirm(client, user, fake_llm):
    action = propose_meal(client, fake_llm)
    client.post("/api/auth/logout")
    make_user(client, "someone@example.com")
    assert client.post(f"/api/actions/{action['id']}/confirm").status_code == 404


def test_stale_proposals_expire(client, user, fake_llm):
    action = propose_meal(client, fake_llm)
    with SessionLocal() as db:
        db.get(PendingAction, action["id"]).created_at = utcnow() - timedelta(hours=25)
        db.commit()
    assert client.post(f"/api/actions/{action['id']}/confirm").status_code == 409


def test_llm_failure_rolls_back_turn(client, user, fake_llm):
    from app.llm.provider import LLMError

    class Broken:
        def complete(self, **_):
            raise LLMError("down")

    from app.llm.provider import set_provider
    set_provider(Broken())
    r = client.post("/api/chat", json={"message": "had an apple"})
    assert r.status_code == 502
    assert client.get("/api/chat/history").json() == []


def test_proposal_ends_turn_in_one_call_and_uses_note(client, user, fake_llm):
    provider = fake_llm(tool_reply("propose_entry", {
        "summary": "Guava", "eaten_at": None, "meal_type": None, "note": "Assumed one medium guava.",
        "items": [{"ingredient_name": "guava", "brand_name": None, "quantity": 1, "unit": "piece",
                   "calories": 68, "protein_g": 2.6, "carbs_g": 14.3, "fat_g": 1, "fiber_g": 5.4}],
    }))
    reply = client.post("/api/chat", json={"message": "had a guava"}).json()[-1]
    assert len(provider.calls) == 1
    assert reply["content"] == "Assumed one medium guava."


def test_calories_that_dont_match_macros_are_sent_back(client, user, fake_llm):
    bad_chicken = {**CHICKEN, "quantity": 150, "calories": 248}   # protein not scaled
    provider = fake_llm(
        tool_reply("propose_entry", {"summary": "x", "eaten_at": None, "meal_type": None, "items": [bad_chicken]}),
        tool_reply("propose_entry", {"summary": "x", "eaten_at": None, "meal_type": None, "items": [CHICKEN_150]},
                   call_id="t2"),
    )
    reply = client.post("/api/chat", json={"message": "150g chicken"}).json()[-1]
    first_result = provider.calls[1]["messages"][-2]["content"][0]   # [-1] is the 2nd assistant turn
    assert first_result["is_error"] is True
    assert "don't agree" in first_result["content"]
    assert reply["actions"][0]["payload"]["totals"]["protein_g"] == 46.5


def test_false_save_claim_is_sent_back_once(client, user, fake_llm):
    provider = fake_llm(
        text_reply("Logged 300 g lauki sabzi. Want me to save it as a recipe?"),
        tool_reply("propose_entry", {"summary": "Lauki sabzi", "eaten_at": None, "meal_type": None,
                                     "note": "Logged your sabzi. Want me to save it as a recipe?",
                                     "items": [CHICKEN]}),
    )
    reply = client.post("/api/chat", json={"message": "my lauki sabzi was 300g lauki"}).json()[-1]
    assert len(provider.calls) == 2
    assert "[App check]" in provider.calls[1]["messages"][-2]["content"]   # [-1] is the retry
    assert len(reply["actions"]) == 1
    assert reply["content"].startswith("Here's your sabzi")      # "Logged" softened


def test_normal_answers_mentioning_logs_are_not_nudged(client, user, fake_llm):
    provider = fake_llm(text_reply("Today you've logged 2 meals, 900 kcal."))
    client.post("/api/chat", json={"message": "how am I doing?"})
    assert len(provider.calls) == 1
