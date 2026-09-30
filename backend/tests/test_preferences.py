"""Optional "about you" questions: all skippable, editable later, and each one used."""
from datetime import datetime, timedelta

from app.db import SessionLocal
from app.models import User
from app.nutrition import age_on, calculate_targets
from app.services.preferences import meal_times
from app.timeutil import infer_meal_type, local_today, utc_to_local
from tests.conftest import ONBOARDING, internal_id, text_reply
from tests.test_dashboard_add import add
from tests.test_routing import chat


def prefs(client, **answers):
    return client.put("/api/profile/preferences", json=answers)


def tdee(sex="male", weight=80, height=180, dob=(1995, 6, 15)) -> float:
    t = calculate_targets(weight_kg=weight, height_cm=height, age=age_on(datetime(*dob).date(), local_today("Asia/Kolkata")),
                          sex=sex, activity_level="moderate", goal_type="maintenance")
    return t.tdee


# --- asked once, skippable, editable later ------------------------------------------------------

def test_offered_once_then_only_in_settings(client, user):
    assert client.get("/api/auth/me").json()["needs_preferences"] is True
    got = client.get("/api/profile/preferences").json()
    assert got["preferences"]["answered"] is False and "vegetarian" in got["options"]["diet_types"]
    assert client.post("/api/profile/preferences/skip").json()["needs_preferences"] is False
    # Skipped, but still editable later (Settings).
    r = prefs(client, diet_type="vegetarian", allergies=["peanut"])
    assert r.status_code == 200 and r.json()["preferences"]["diet_type"] == "vegetarian"
    assert client.get("/api/auth/me").json()["needs_preferences"] is False


def test_every_answer_is_optional_and_checked(client, user):
    assert prefs(client).status_code == 200                                     # nothing filled in
    for bad in ({"diet_type": "carnivore"}, {"allergies": ["kiwi"]}, {"pace_kg_per_week": 3},
                {"training_days": [7]}, {"breakfast_time": "8am"},
                {"breakfast_time": "09:00", "lunch_time": "10:00"},             # less than 2 h apart
                {"pregnancy": "pregnant", "health_consent": True}):            # male profile
        assert prefs(client, **bad).status_code == 422, bad


def test_health_details_need_an_explicit_ok(client, user):
    r = prefs(client, health_conditions=["diabetes"])
    assert r.status_code == 422 and "tick the box" in r.json()["detail"]
    assert prefs(client, health_conditions=["diabetes"], health_consent=True).json()["preferences"]["health_consent"]
    # Removing them removes the consent too (nothing sensitive is stored any more).
    assert prefs(client, diet_type="vegan").json()["preferences"]["health_consent"] is False


# --- used: targets ----------------------------------------------------------------------------------

def test_pace_sets_the_calorie_target(client, user):
    r = prefs(client, pace_kg_per_week=0.25).json()                           # goal: weight loss (-20% by default)
    assert r["suggested_targets"]["daily_calorie_target"] == round((tdee() - 275) / 10) * 10
    # 0.5 kg/week (-550) is within 50 kcal of the current -20% target: nothing to suggest.
    assert prefs(client, pace_kg_per_week=0.5).json()["suggested_targets"] is None
    capped = prefs(client, pace_kg_per_week=1.0).json()["suggested_targets"]["daily_calorie_target"]
    assert capped == round(tdee() * 0.75 / 10) * 10                          # never more than 25% below
    # Accepting it saves the formula's targets.
    me = client.post("/api/profile/recalculate-targets").json()
    assert me["targets"]["calories"] == capped and me["targets"]["is_custom"] is False


def test_no_deficit_while_pregnant(client):
    client.post("/api/auth/register", json={"email": "f@example.com", "password": "password123", "consent": True})
    client.post("/api/profile/onboarding", json={**ONBOARDING, "sex": "female", "weight_kg": 70, "height_cm": 165})
    r = prefs(client, pregnancy="pregnant", pace_kg_per_week=0.5, health_consent=True).json()
    assert r["suggested_targets"]["daily_calorie_target"] == round(tdee("female", 70, 165) / 10) * 10


# --- used: meal times -----------------------------------------------------------------------------------

def test_meal_times_decide_the_meal(client, user):
    prefs(client, breakfast_time="10:30", lunch_time="14:30", dinner_time="21:30")
    with SessionLocal() as db:
        times = meal_times(db.get(User, internal_id(user["id"])))
    noon = datetime(2026, 9, 30, 12, 0)
    assert infer_meal_type(noon) == "lunch" and infer_meal_type(noon, times) == "breakfast"
    assert infer_meal_type(datetime(2026, 9, 30, 21, 0), times) == "dinner"
    # The Dashboard puts food added to an empty meal at the user's usual time.
    yesterday = (local_today("Asia/Kolkata") - timedelta(days=1)).isoformat()
    client.post(f"/api/actions/{chat(client, '150 g banana')['actions'][0]['id']}/confirm")
    add(client, name="banana", quantity=100, unit="g", meal_type="dinner", day=yesterday)
    entry = next(e for e in client.get(f"/api/dashboard/daily?day={yesterday}").json()["entries"])
    assert entry["eaten_at"][11:16] == "21:30"


# --- used: MacBro and cards --------------------------------------------------------------------------------

def test_macbro_sees_what_was_shared(client, user, fake_llm):
    prefs(client, diet_type="jain", allergies=["milk"], allergy_notes="mushrooms",
          training_days=[0, 2, 4], training_type="strength")
    llm = fake_llm(text_reply("Try moong dal chilla."))
    chat(client, "what should I have for dinner?")
    context = llm.calls[0]["system_dynamic"]
    assert "Diet: Jain" in context and "Milk / dairy (lactose), mushrooms" in context
    assert "Strength / weights · Mon, Wed, Fri" in context


def test_cards_flag_a_listed_allergen(client, user, fake_llm):
    prefs(client, allergies=["milk"])
    fake_llm()
    reply = chat(client, "had 200 g curd")                                     # general list, no AI
    assert "Heads-up: curd usually contains milk / dairy" in reply["content"]
    assert "Heads-up" not in chat(client, "had 150 g banana")["content"]


def test_export_includes_the_answers(client, user):
    prefs(client, diet_type="vegan")
    assert client.get("/api/profile/export").json()["about_you"]["diet_type"] == "vegan"
