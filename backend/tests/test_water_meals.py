"""Water tracker, five meal types, and relabelling of legacy 'snack' entries."""
from datetime import datetime

import pytest

from app.db import SessionLocal
from app.data_migrations import relabel_legacy_snacks
from app.models import LogEntry, LogEntryItem
from app.services.water import water_target_ml
from app.timeutil import local_to_utc, resolve_meal_type
from tests.conftest import text_reply, tool_reply
from tests.test_foods import CHICKEN, chat_propose


def test_water_target_from_weight_and_activity():
    assert water_target_ml(60, "light") == 2350       # 60*35 + 250
    assert water_target_ml(80, "moderate") == 3300    # 80*35 + 500
    assert water_target_ml(None, "light") is None


@pytest.mark.parametrize("stated,hour,expected", [
    ("snack", 11, "morning_snack"), ("snack", 16, "evening_snack"), ("snack", 13, "evening_snack"),
    ("snack", 8, "morning_snack"), ("dinner", 16, "dinner"), (None, 8, "breakfast"),
])
def test_resolve_meal_type(stated, hour, expected):
    assert resolve_meal_type(stated, datetime(2026, 1, 1, hour, 0)) == expected


def test_water_from_chat_needs_confirmation(client, user, fake_llm):
    action = chat_propose(client, fake_llm, "propose_water", {"amount_ml": 1000, "drank_at": None})
    assert action["action_type"] == "water"
    water = lambda: client.get("/api/dashboard/daily").json()["water"]
    assert water()["consumed_ml"] == 0
    client.post(f"/api/actions/{action['id']}/confirm")
    w = water()
    assert w["consumed_ml"] == 1000 and w["target_ml"] == 80 * 35 + 500


def test_water_amount_is_validated(client, user, fake_llm):
    provider = fake_llm(tool_reply("propose_water", {"amount_ml": 90000, "drank_at": None, "note": ""}),
                        text_reply("How much was it?"))
    client.post("/api/chat", json={"message": "drank a lake"})
    assert provider.calls[1]["messages"][-1]["content"][0]["is_error"] is True


def test_quick_water_buttons_and_undo(client, user):
    r = client.post("/api/water", json={"amount_ml": 250})
    assert r.status_code == 201
    client.post("/api/water", json={"amount_ml": 500})
    assert client.get("/api/dashboard/daily").json()["water"]["consumed_ml"] == 750
    assert client.delete(f"/api/water/{r.json()['id']}").status_code == 200
    assert client.get("/api/dashboard/daily").json()["water"]["consumed_ml"] == 500
    assert client.post("/api/water", json={"amount_ml": 0}).status_code == 422


def test_plain_snack_is_stored_as_morning_or_evening(client, user, fake_llm):
    action = chat_propose(client, fake_llm, "propose_entry", {
        "summary": "s", "eaten_at": None, "meal_type": "snack", "items": [CHICKEN],
    })
    assert action["payload"]["meal_type"] in ("morning_snack", "evening_snack")


def test_legacy_snack_entries_are_relabelled(client, user):
    with SessionLocal() as db:
        uid = user["id"]
        for local_hour in (11, 17):
            db.add(LogEntry(user_id=uid, meal_type="snack",
                            eaten_at=local_to_utc(datetime(2026, 9, 28, local_hour, 0), "Asia/Kolkata"),
                            items=[LogEntryItem(ingredient_name="nuts", quantity=10, unit="g", calories=60,
                                                protein_g=2, carbs_g=2, fat_g=5, fiber_g=1)]))
        db.commit()
        assert relabel_legacy_snacks(db) == 2
        assert sorted(e.meal_type for e in db.query(LogEntry).all()) == ["evening_snack", "morning_snack"]
        assert relabel_legacy_snacks(db) == 0


def test_water_missed_alongside_food_is_asked_for_once(client, user, fake_llm):
    provider = fake_llm(
        tool_reply("propose_entry", {"summary": "idli", "eaten_at": None, "meal_type": "breakfast",
                                     "note": "Here's breakfast.", "items": [CHICKEN]}),
        tool_reply("propose_water", {"amount_ml": 500, "drank_at": None, "note": "And 500 ml water."}, call_id="t2"),
    )
    reply = client.post("/api/chat", json={"message": "had idlis and 2 glasses of water"}).json()[-1]
    assert len(provider.calls) == 2
    assert sorted(a["action_type"] for a in reply["actions"]) == ["create", "water"]
    assert "Here's breakfast." in reply["content"] and "500 ml water" in reply["content"]


def test_no_water_check_when_water_not_mentioned(client, user, fake_llm):
    provider = fake_llm(tool_reply("propose_entry", {"summary": "c", "eaten_at": None, "meal_type": None,
                                                     "note": "ok", "items": [CHICKEN]}))
    client.post("/api/chat", json={"message": "had chicken"})
    assert len(provider.calls) == 1


def test_food_note_kept_when_model_says_no_drinking_water(client, user, fake_llm):
    fake_llm(
        tool_reply("propose_entry", {"summary": "c", "eaten_at": None, "meal_type": None,
                                     "note": "Here's your coconut water.", "items": [CHICKEN]}),
        text_reply("No plain water there."),
    )
    reply = client.post("/api/chat", json={"message": "had coconut water"}).json()[-1]
    assert reply["content"].startswith("Here's your coconut water.")
    assert len(reply["actions"]) == 1
