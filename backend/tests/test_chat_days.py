"""Chat per day: fresh chat each day, earlier days on request, and the date picker."""
from datetime import timedelta

from app.db import SessionLocal
from app.models import ChatMessage, User, utcnow
from app.timeutil import local_today
from tests.conftest import text_reply


def _age_messages(days: int):
    """Pretend every message so far was sent `days` days ago."""
    with SessionLocal() as db:
        for m in db.query(ChatMessage).all():
            m.created_at = utcnow() - timedelta(days=days)
        db.commit()


def test_each_day_starts_fresh_and_earlier_days_load(client, user, fake_llm):
    fake_llm(text_reply("Hey!"), text_reply("Morning!"))
    client.post("/api/chat", json={"message": "hi"})
    _age_messages(2)
    llm = fake_llm(text_reply("Morning!"))
    client.post("/api/chat", json={"message": "good morning"})

    today = client.get("/api/chat/day").json()
    assert [m["content"] for m in today["messages"]] == ["good morning", "Morning!"]
    assert today["prev_day"] == (local_today("Asia/Kolkata") - timedelta(days=2)).isoformat()
    earlier = client.get(f"/api/chat/day?day={today['prev_day']}").json()
    assert [m["content"] for m in earlier["messages"]] == ["hi", "Hey!"]
    assert earlier["prev_day"] is None
    # The model also starts fresh: the old conversation isn't sent.
    sent = [m["content"] for m in llm.calls[0]["messages"]]
    assert "hi" not in sent and "good morning" in sent


def test_picked_date_reaches_the_model(client, user, fake_llm):
    yesterday = (local_today("Asia/Kolkata") - timedelta(days=1)).isoformat()
    llm = fake_llm(text_reply("Which meal?"))
    out = client.post("/api/chat", json={"message": "had 2 eggs", "log_date": yesterday}).json()
    assert out[0]["role"] == "user" and out[0]["data"] == {"log_date": yesterday}
    call = llm.calls[0]
    assert '"selected_date"' in call["system_dynamic"] and yesterday in call["system_dynamic"]
    assert call["messages"][-1]["content"] == f"[Date picked in the app: {yesterday}] had 2 eggs"


def test_today_or_future_date_is_not_a_selection(client, user, fake_llm):
    tomorrow = (local_today("Asia/Kolkata") + timedelta(days=1)).isoformat()
    llm = fake_llm(text_reply("ok"))
    out = client.post("/api/chat", json={"message": "hi", "log_date": tomorrow}).json()
    assert out[0]["data"] is None and '"selected_date"' not in llm.calls[0]["system_dynamic"]
