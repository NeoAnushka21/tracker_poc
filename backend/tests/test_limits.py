"""Daily AI allowance (per user, per local day) and sign-in attempt limits."""
from datetime import timedelta

import pytest

from app import config
from app.db import SessionLocal
from app.models import AiRequest, User, utcnow
from app.llm.provider import LLMError, set_provider
from tests.conftest import make_user, text_reply
from tests.test_dashboard_add import add, estimate_reply


@pytest.fixture
def limit_2(monkeypatch):
    monkeypatch.setattr(config, "AI_DAILY_MESSAGE_LIMIT", 2)


def chat(client, text="what should I eat?"):
    return client.post("/api/chat", json={"message": text})


def allowance(client):
    return client.get("/api/chat/allowance").json()


# --- daily AI allowance --------------------------------------------------------------

def test_ai_messages_are_counted_and_capped(client, user, fake_llm, limit_2):
    assert allowance(client) | {"resets_at": None} == {"limit": 2, "used": 0, "remaining": 2, "resets_at": None}
    provider = fake_llm(text_reply("Eggs!"), text_reply("Dal!"))
    assert chat(client).status_code == 200 and chat(client).status_code == 200
    assert allowance(client)["remaining"] == 0

    r = chat(client, "and dinner?")
    assert r.status_code == 429 and "all 2 AI messages for today" in r.json()["detail"]
    assert len(provider.calls) == 2                                   # no model call once it's used up
    texts = [m["content"] for m in client.get("/api/chat/history").json()]
    assert "and dinner?" not in texts                                  # nothing saved for the refused message


def test_instant_replies_and_buttons_never_count(client, user, fake_llm, limit_2):
    fake_llm()                                                         # any model call would fail
    assert chat(client, "drank 500 ml water").status_code == 200       # fast path
    assert chat(client, "what's left today").status_code == 200        # fast path
    assert client.post("/api/water", json={"amount_ml": 250}).status_code in (200, 201)
    assert allowance(client)["used"] == 0


def test_failed_ai_calls_dont_count(client, user, limit_2):
    class Broken:
        def complete(self, **_):
            raise LLMError("down")

    set_provider(Broken())
    try:
        assert chat(client).status_code == 503
    finally:
        set_provider(None)
    assert allowance(client)["used"] == 0


def test_dashboard_estimates_count_saved_foods_dont(client, user, fake_llm, limit_2):
    fake_llm(estimate_reply(), estimate_reply())
    action = add(client, name="paneer").json()["action"]
    client.post(f"/api/actions/{action['id']}/confirm")               # paneer is now a saved food
    assert allowance(client)["used"] == 1
    assert add(client, name="paneer").json()["status"] == "added"      # saved: no AI, not counted
    assert allowance(client)["used"] == 1
    assert add(client, name="tofu").json()["status"] == "estimate"
    r = add(client, name="tempeh")
    assert r.status_code == 429 and "AI messages" in r.json()["detail"]


def test_allowance_resets_on_a_new_day_and_is_per_user(client, user, fake_llm, limit_2):
    with SessionLocal() as db:
        uid = db.query(User).filter_by(email="me@example.com").one().id
        for _ in range(2):   # two uses yesterday
            db.add(AiRequest(user_id=uid, kind="chat", created_at=utcnow() - timedelta(days=1)))
        db.commit()
    assert allowance(client)["used"] == 0

    fake_llm(text_reply("a"), text_reply("b"))
    chat(client), chat(client)
    client.post("/api/auth/logout")
    make_user(client, "other@example.com")
    assert allowance(client)["used"] == 0                               # someone else's count is separate


def test_zero_means_unlimited(client, user, fake_llm, monkeypatch):
    monkeypatch.setattr(config, "AI_DAILY_MESSAGE_LIMIT", 0)
    assert allowance(client)["limit"] is None and allowance(client)["remaining"] is None
    fake_llm(*[text_reply("ok") for _ in range(3)])
    assert all(chat(client).status_code == 200 for _ in range(3))


# --- sign-in attempt limits ------------------------------------------------------------

def test_wrong_passwords_pause_that_email(client, user, monkeypatch):
    monkeypatch.setattr(config, "LOGIN_FAILURES_PER_EMAIL", 3)
    bad = {"email": "me@example.com", "password": "wrong-password"}
    assert [client.post("/api/auth/login", json=bad).status_code for _ in range(3)] == [401, 401, 401]
    r = client.post("/api/auth/login", json={"email": "me@example.com", "password": "password123"})
    assert r.status_code == 429 and "Too many attempts" in r.json()["detail"]   # even the right one, for now
    # Other accounts aren't affected.
    assert client.post("/api/auth/login", json={"email": "nobody@example.com", "password": "x" * 8}).status_code == 401


def test_success_clears_the_failure_count(client, user, monkeypatch):
    monkeypatch.setattr(config, "LOGIN_FAILURES_PER_EMAIL", 3)
    bad = {"email": "me@example.com", "password": "wrong-password"}
    good = {"email": "me@example.com", "password": "password123"}
    client.post("/api/auth/login", json=bad), client.post("/api/auth/login", json=bad)
    assert client.post("/api/auth/login", json=good).status_code == 200
    client.post("/api/auth/login", json=bad), client.post("/api/auth/login", json=bad)
    assert client.post("/api/auth/login", json=good).status_code == 200


def test_requests_per_address_are_capped(client, monkeypatch):
    monkeypatch.setattr(config, "AUTH_REQUESTS_PER_IP", 3)
    body = {"email": "x@example.com", "password": "password123"}
    codes = [client.post("/api/auth/login", json=body, headers={"X-Forwarded-For": "203.0.113.5"}).status_code
             for _ in range(4)]
    assert codes == [401, 401, 401, 429]
    # A different address still gets in.
    assert client.post("/api/auth/login", json=body, headers={"X-Forwarded-For": "198.51.100.7"}).status_code == 401
