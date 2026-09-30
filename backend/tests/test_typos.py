"""Typos in saved-food names are matched in plain Python, so they don't use an AI message."""
from app.db import SessionLocal
from app.models import User
from app.services.foods import closest_saved, edit_distance, library_context, typo_limit
from tests.test_dashboard_add import PANEER, add, estimate_reply, meal_items
from tests.test_foods import CHICKEN, log_and_confirm
from tests.test_limits import allowance
from tests.test_routing import EGG, chat


# --- the matcher ------------------------------------------------------------------------

def test_edit_distance_counts_typos_and_swaps():
    assert edit_distance("panner", "paneer", 1) == 1        # one letter changed
    assert edit_distance("panere", "paneer", 1) == 1        # two neighbours swapped
    assert edit_distance("chiken", "chicken", 1) == 1       # one letter dropped
    assert edit_distance("banana", "paneer", 2) == 3        # stops early: more than the limit


def test_short_words_must_match_exactly():
    assert typo_limit("egg") == 0 and typo_limit("paneer") == 1 and typo_limit("chicken breast") == 2
    index = {"fig": "Fig", "figs": "Fig"}
    assert closest_saved(index, "egg") is None               # 'egg' vs 'fig' are different foods


def test_a_typo_never_picks_between_two_close_foods():
    index = {"paneer": "Paneer", "panner": "Panner Tikka"}
    assert closest_saved(index, "Paneer") == "Paneer"        # exact still wins
    assert closest_saved(index, "panmer") is None            # close to both: don't guess
    assert closest_saved({"paneer": "Paneer"}, "PANER") == "Paneer"


# --- chat: saved-food fast path ---------------------------------------------------------

def test_chat_typo_of_saved_food_uses_no_ai(client, user, fake_llm):
    log_and_confirm(client, fake_llm, [EGG, CHICKEN])
    used = allowance(client)["used"]
    no = fake_llm()                                          # any model call would fail
    reply = chat(client, "had 3 eggs and 200 g chiken breast for lunch")
    [card] = reply["actions"]
    items = card["payload"]["items"]
    assert [(i["ingredient_name"], i["quantity"]) for i in items] == [("eggs, large", 3), ("chicken breast, cooked", 200)]
    assert items[1]["calories"] == 330                        # numbers from the saved food
    assert "I read 'chiken breast' as chicken breast, cooked" in reply["content"]
    assert no.calls == [] and allowance(client)["used"] == used


def test_chat_short_word_typo_still_goes_to_the_model(client, user, fake_llm):
    log_and_confirm(client, fake_llm, [EGG])
    llm = fake_llm(estimate_reply())
    chat(client, "had 3 egs")                                  # 'egs' is too short to guess
    assert len(llm.calls) == 1


def test_ai_sees_saved_foods_despite_a_typo(client, user, fake_llm):
    log_and_confirm(client, fake_llm, [PANEER])
    with SessionLocal() as db:
        u = db.query(User).one()
        lines = library_context(db, u, "had some panner curry")
        assert len(lines) == 1 and "| paneer |" in lines[0]
        assert library_context(db, u, "had some rice") == []


# --- Dashboard: "Did you mean …?" ----------------------------------------------------------

def test_dashboard_typo_asks_before_adding(client, user, fake_llm):
    log_and_confirm(client, fake_llm, [PANEER])
    no = fake_llm()
    r = add(client, name="panner", meal_type="dinner")
    assert r.json()["status"] == "suggest" and r.json()["food"]["name"] == "paneer"
    assert meal_items(client, "dinner") == [] and no.calls == []   # nothing added, no AI

    food_id = r.json()["food"]["id"]
    assert add(client, name="paneer", food_id=food_id, meal_type="dinner").json()["status"] == "added"
    assert [i["ingredient_name"] for i in meal_items(client, "dinner")] == ["paneer"]


def test_dashboard_no_thanks_estimates_the_typed_name(client, user, fake_llm):
    log_and_confirm(client, fake_llm, [PANEER])
    llm = fake_llm(estimate_reply())
    r = add(client, name="panner", meal_type="dinner", as_typed=True)
    assert r.json()["status"] == "estimate" and len(llm.calls) == 1


# --- meal words ---------------------------------------------------------------------------

def test_meal_word_typos_are_fixed_only_where_a_meal_is_expected():
    from app.llm.fastpath import _fix_meal_typos as fix
    cases = {
        "3 eggs for breakfst": "3 eggs for breakfast",       # a letter missing
        "2 eggs for bekfast": "2 eggs for breakfast",        # two letters off
        "2 eggs for brkfst": "2 eggs for breakfast",         # vowels dropped
        "2 eggs for bfast": "2 eggs for breakfast",          # common shorthand
        "1 roti at dinr": "1 roti at dinner",
        "3 eggs for lnch": "3 eggs for lunch",
        "1 apple for my snak": "1 apple for my snack",
        "2 eggs for mornng snak": "2 eggs for morning snack",
        "same brkfst as yesterday": "same breakfast as yesterday",
    }
    assert {t: fix(t) for t in cases} == cases
    for untouched in ("a bunch of grapes", "fruit punch for lunch", "2 eggs for brunch"):
        assert fix(untouched) == untouched                   # not after for/at/…, or not close enough


def test_chat_meal_typo_uses_no_ai(client, user, fake_llm):
    log_and_confirm(client, fake_llm, [EGG])
    no = fake_llm()
    assert chat(client, "had 3 eggs for brkfst")["actions"][0]["payload"]["meal_type"] == "breakfast"
    assert chat(client, "2 eggs for mornng snak")["actions"][0]["payload"]["meal_type"] == "morning_snack"
    assert no.calls == []
