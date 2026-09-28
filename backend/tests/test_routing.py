"""Multi-model routing: rule-based fast paths, tier routing, tool/prompt subsets, the model
pool (failover, cooldowns, open-source licences) and usage logging. All with fake models."""
from datetime import timedelta

import pytest

from app.db import SessionLocal
from app.llm import pool as pool_module
from app.llm.pool import ModelPool, ModelSlot, is_open_source
from app.llm.provider import LLMError, LLMRateLimited
from app.llm.router import route
from app.models import LlmUsage, LogEntry, LogEntryItem, User
from app.timeutil import local_day_bounds_utc, local_today
from tests.conftest import FakeProvider, text_reply, tool_reply
from tests.test_admin import admin_emails  # noqa: F401  (fixture)
from tests.test_foods import CHICKEN, log_and_confirm

EGG = {"ingredient_name": "eggs, large", "brand_name": None, "quantity": 2, "unit": "piece",
       "calories": 144, "protein_g": 12.6, "carbs_g": 0.8, "fat_g": 9.6, "fiber_g": 0,
       "food_id": None, "unit_weight_g": 50}


@pytest.fixture
def no_llm(fake_llm):
    """A fake with no scripted replies: any model call fails the test."""
    return fake_llm()


def chat(client, text, **kw):
    r = client.post("/api/chat", json={"message": text, **kw})
    assert r.status_code == 200, r.text
    return r.json()[-1]


def usage_rows():
    with SessionLocal() as db:
        return [(u.provider, u.model, u.tier, u.intent, u.outcome) for u in db.query(LlmUsage).order_by(LlmUsage.id)]


# --- router --------------------------------------------------------------------

@pytest.mark.parametrize("text,intent,tier", [
    ("had 2 eggs", "log", "small"),
    ("150g chicken breast", "log", "small"),
    ("had a sandwich for lunch", "log", "large"),                       # vague contents
    ("2 rotis, dal, rice and some sabzi", "log", "large"),              # 3+ foods
    ("oats for breakfast and a banana for lunch", "log", "large"),     # two meals
    ("had oats", "log", "large"),                                        # no amount
    ("what did I eat yesterday?", "query", "small"),
    ("how much protein did I have this week", "query", "small"),
    ("move the banana to breakfast", "edit", "small"),
    ("delete the cookie", "edit", "small"),
    ("the rice was actually 200g", "edit", "small"),
    ("save my chapati as a recipe", "full", "large"),
])
def test_router(text, intent, tier):
    r = route(text)
    assert (r.intent, r.tier) == (intent, tier), r.reason


def test_feedback_always_goes_large():
    assert route("make it 3", feedback=True).tier == "large"


# --- fast paths (no model call) ----------------------------------------------------

@pytest.mark.parametrize("text,ml", [
    ("drank 500 ml water", 500), ("2 glasses of water", 500), ("a bottle of water", 500),
    ("1.5 l water", 1500), ("had a glass of water.", 250), ("1 litre of water", 1000),
])
def test_water_fastpath(client, user, no_llm, text, ml):
    reply = chat(client, text)
    assert reply["actions"][0]["action_type"] == "water"
    assert reply["actions"][0]["payload"]["amount_ml"] == ml
    assert no_llm.calls == []
    assert usage_rows()[-1] == ("fastpath", "water", "none", "water", "fastpath")


def test_water_with_food_goes_to_the_model(client, user, fake_llm):
    llm = fake_llm(text_reply("Which meal?"))
    chat(client, "had 2 eggs and a glass of water")
    assert len(llm.calls) == 1


def test_yes_nudge_only_with_a_pending_card(client, user, fake_llm):
    fake_llm(tool_reply("propose_entry", {"summary": "Chicken", "eaten_at": None, "meal_type": None,
                                          "items": [CHICKEN], "note": "Here you go."}))
    chat(client, "150g chicken breast")
    no = fake_llm()
    assert "Looks good" in chat(client, "yes")["content"] and no.calls == []
    # With nothing pending, "yes" is an answer to a question and goes to the model.
    client.post("/api/actions/1/reject")
    llm = fake_llm(text_reply("Great!"))
    chat(client, "yes")
    assert len(llm.calls) == 1


def test_summary_fastpath(client, user, no_llm):
    reply = chat(client, "how much protein is left?")
    assert reply["content"].startswith("Protein: 0 /") and "Calories:" in reply["content"]
    assert "Here's today so far" in chat(client, "what's left today")["content"]
    assert no_llm.calls == []


def test_library_only_log_fastpath(client, user, fake_llm):
    log_and_confirm(client, fake_llm, [EGG, CHICKEN])
    no = fake_llm()
    reply = chat(client, "had 3 eggs for breakfast")
    card = reply["actions"][0]
    assert card["action_type"] == "create" and card["payload"]["meal_type"] == "breakfast"
    item = card["payload"]["items"][0]
    assert (item["quantity"], item["unit"], item["source"]) == (3, "piece", "library")
    assert item["protein_g"] == pytest.approx(12.6 * 1.5, abs=0.1)
    assert no.calls == []
    # Two saved foods in one message (the comma-free alias "chicken breast" works too).
    items = chat(client, "3 eggs and 200 g chicken breast")["actions"][0]["payload"]["items"]
    assert [(i["ingredient_name"], i["quantity"]) for i in items] == [("eggs, large", 3), ("chicken breast, cooked", 200)]
    assert no.calls == []


def test_unknown_food_goes_to_the_model(client, user, fake_llm):
    llm = fake_llm(text_reply("How big was the mango?"))
    chat(client, "had 1 mango")
    assert len(llm.calls) == 1


def test_same_meal_as_yesterday(client, user, no_llm):
    with SessionLocal() as db:
        u = db.query(User).one()
        day = local_today(u.timezone) - timedelta(days=1)
        start, _ = local_day_bounds_utc(day, u.timezone)
        e = LogEntry(user_id=u.id, eaten_at=start + timedelta(hours=8), meal_type="breakfast")
        e.items.append(LogEntryItem(ingredient_name="poha", quantity=1, unit="plate", calories=250,
                                    protein_g=5, carbs_g=45, fat_g=6, fiber_g=2))
        db.add(e)
        db.commit()
    card = chat(client, "same breakfast as yesterday")["actions"][0]
    assert card["action_type"] == "copy" and card["payload"]["to_date"] == local_today("Asia/Kolkata").isoformat()
    assert "nothing to copy" in chat(client, "repeat yesterday's dinner")["content"]
    assert no_llm.calls == []


# --- slimmer calls ---------------------------------------------------------------

def test_query_gets_only_read_tools_and_a_short_prompt(client, user, fake_llm):
    llm = fake_llm(text_reply("You had oats."))
    chat(client, "what did I eat yesterday?")
    call = llm.calls[0]
    assert {t["name"] for t in call["tools"]} == {"get_logs", "get_daily_summary", "get_food"}
    assert "## Questions about past data" in call["system_stable"]
    assert "## Recipes" not in call["system_stable"] and "## Logging food" not in call["system_stable"]


def test_simple_log_gets_logging_tools(client, user, fake_llm):
    llm = fake_llm(text_reply("Which meal?"))
    chat(client, "had 2 eggs")
    assert {t["name"] for t in llm.calls[0]["tools"]} == {"propose_entry", "propose_water", "get_food"}


# --- pool, failover, licences, escalation ----------------------------------------------

class Named(FakeProvider):
    def __init__(self, model, script=(), error=None):
        super().__init__(list(script))
        self.provider_name, self.model, self.error = "fake", model, error

    def complete(self, **kw):
        if self.error:
            self.calls.append(kw)
            raise self.error
        return super().complete(**kw)


@pytest.fixture
def install_pool():
    def install(*slots):
        pool_module.set_pool(ModelPool(list(slots)))
    yield install
    pool_module.set_pool(None)


def test_rate_limited_model_cools_down_and_the_next_one_answers(client, user, install_pool):
    limited = Named("gpt-oss-20b", error=LLMRateLimited("used up", retry_after=900))
    backup = Named("qwen3-32b", [text_reply("Which meal?"), text_reply("Which meal?")])
    install_pool(ModelSlot(limited, "small"), ModelSlot(backup, "small"))
    chat(client, "had 2 eggs")
    chat(client, "had 2 eggs")
    assert len(limited.calls) == 1              # skipped while cooling down
    assert len(backup.calls) == 2
    outcomes = [(m, o) for _, m, _, _, o in usage_rows()]
    assert outcomes == [("gpt-oss-20b", "rate_limited"), ("qwen3-32b", "ok"), ("qwen3-32b", "ok")]


def test_small_tier_down_falls_back_to_large(client, user, install_pool):
    small = Named("gpt-oss-20b", error=LLMError("boom"))
    large = Named("gpt-oss-120b", [text_reply("Which meal?")])
    install_pool(ModelSlot(small, "small"), ModelSlot(large, "large"))
    chat(client, "had 2 eggs")
    assert len(large.calls) == 1


def test_all_models_down_shows_the_friendly_message(client, user, install_pool):
    install_pool(ModelSlot(Named("gpt-oss-20b", error=LLMError("boom")), "small"))
    r = client.post("/api/chat", json={"message": "had 2 eggs"})
    assert r.status_code == 503 and "temporarily down" in r.json()["detail"]
    assert usage_rows()[-1][-1] == "error"      # failed calls are still counted


def test_escalates_to_large_after_repeated_validation_errors(client, user, install_pool):
    bad = {"summary": "x", "eaten_at": None, "meal_type": None, "items": []}   # invalid: no items
    small = Named("gpt-oss-20b", [tool_reply("propose_entry", bad, "a"), tool_reply("propose_entry", bad, "b")])
    large = Named("gpt-oss-120b", [tool_reply("propose_entry", {
        "summary": "Eggs", "eaten_at": None, "meal_type": None, "items": [EGG], "note": "Here."}, "c")])
    install_pool(ModelSlot(small, "small"), ModelSlot(large, "large"))
    reply = chat(client, "had 2 eggs")
    assert len(small.calls) == 2 and len(large.calls) == 1
    assert reply["actions"][0]["action_type"] == "create"
    assert large.calls[0]["tools"][0]["name"] == "propose_entry" and len(large.calls[0]["tools"]) > 3
    with SessionLocal() as db:
        assert db.query(LlmUsage).filter_by(escalated=True).count() == 1


@pytest.mark.parametrize("model,ok", [
    ("openai/gpt-oss-120b", True), ("qwen/qwen3-32b", True), ("deepseek/deepseek-chat", True),
    ("mistralai/mistral-small", True), ("llama-3.3-70b-versatile", False),
    ("deepseek-ai/deepseek-v4.1-flash", True), ("z-ai/glm-5.3-flash", True), ("z-ai/glm-5.3", False),
    ("mistralai/mistral-large-2-instruct", False), ("mistralai/codestral-22b-instruct-v0.1", False),
    ("nvidia/mistral-nemo-minitron-8b-8k-instruct", False), ("nvidia/nemotron-3-super-120b-a12b", False),
    ("deepseek-ai/deepseek-coder-6.7b-instruct", False), ("qwen/qwen2.5-72b-instruct", False),
    ("moonshotai/kimi-k3", False), ("writer/palmyra-med-70b", False),
    ("deepseek-r1-distill-llama-70b", False), ("google/gemma-3-27b", False), ("some-closed-model", False),
])
def test_only_open_source_licences_are_allowed(model, ok):
    assert is_open_source(model) is ok


def test_build_pool_drops_non_open_source(monkeypatch):
    from app import config
    monkeypatch.setattr(config, "LLM_PROVIDER", "openai_compatible")
    monkeypatch.setattr(config, "LLM_SMALL_MODELS", ["llama-3.1-8b-instant", "openai/gpt-oss-20b"])
    monkeypatch.setattr(config, "LLM_LARGE_MODELS", ["openai/gpt-oss-120b"])
    monkeypatch.setattr(config, "LLM_POOL_FILE", "does-not-exist.json")
    models = [(s.tier, s.provider.model) for s in pool_module.build_pool().slots]
    assert models == [("small", "openai/gpt-oss-20b"), ("large", "openai/gpt-oss-120b")]


# --- admin view ---------------------------------------------------------------------

def test_admin_usage_report(client, user, fake_llm, admin_emails):
    from tests.test_admin import login_admin
    fake_llm(text_reply("Which meal?"))
    chat(client, "had 2 eggs")
    chat(client, "drank 500 ml water")
    assert client.get("/api/admin/llm-usage").status_code == 403      # normal users can't see it
    login_admin(client)
    rep = client.get("/api/admin/llm-usage").json()
    assert rep["totals"]["user_messages"] == 2 and rep["totals"]["model_calls"] == 1
    assert rep["totals"]["fastpath_replies"] == 1 and rep["totals"]["fastpath_share_pct"] == 50
    assert rep["fastpath"] == {"water": 1}
    assert rep["by_intent"] == [{"intent": "log", "calls": 1, "tokens": 0}]
    assert all(p["tier"] in ("small", "large") for p in rep["pool"])


def test_backup_models_only_after_every_primary(client, user, install_pool):
    """A slow backup host (priority 2) never takes normal traffic, even from the other tier."""
    small = Named("gpt-oss-20b", error=LLMRateLimited("used up", retry_after=600))
    large = Named("gpt-oss-120b", [text_reply("Which meal?")])
    backup = Named("deepseek-v4.1-flash", [text_reply("Which meal?")])
    install_pool(ModelSlot(small, "small"), ModelSlot(backup, "large", priority=2), ModelSlot(large, "large"))
    chat(client, "had 2 eggs")
    assert (len(large.calls), len(backup.calls)) == (1, 0)
    large.error = LLMError("down")
    chat(client, "had 2 eggs")
    assert len(backup.calls) == 1


def test_pool_file_backup_entries(tmp_path, monkeypatch):
    import json
    from app import config
    f = tmp_path / "pool.json"
    f.write_text(json.dumps({"models": [
        {"provider": "nvidia", "tier": "large", "priority": 2, "timeout_s": 90, "base_url": "https://x/v1",
         "model": "deepseek-ai/deepseek-v4.1-flash", "api_key_env": "TEST_POOL_KEY"},
        {"provider": "nvidia", "tier": "large", "base_url": "https://x/v1",
         "model": "z-ai/glm-5.3", "api_key_env": "TEST_POOL_KEY"},             # custom licence: dropped
        {"provider": "other", "tier": "small", "base_url": "https://y/v1",
         "model": "qwen/qwen3-32b", "api_key_env": "MISSING_KEY"},              # no key: skipped
    ]}))
    monkeypatch.setenv("TEST_POOL_KEY", "k")
    monkeypatch.setattr(config, "LLM_PROVIDER", "openai_compatible")
    monkeypatch.setattr(config, "LLM_SMALL_MODELS", ["openai/gpt-oss-20b"])
    monkeypatch.setattr(config, "LLM_LARGE_MODELS", ["openai/gpt-oss-120b"])
    monkeypatch.setattr(config, "LLM_POOL_FILE", str(f))
    slots = pool_module.build_pool().slots
    assert [(s.provider.model, s.priority) for s in slots] == [
        ("openai/gpt-oss-20b", 1), ("openai/gpt-oss-120b", 1), ("deepseek-ai/deepseek-v4.1-flash", 2)]
    assert slots[2].provider.timeout == 90 and slots[2].provider.provider_name == "nvidia"
