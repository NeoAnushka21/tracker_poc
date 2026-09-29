"""Privacy: adults only (date of birth checked), and Download my data."""
from datetime import date, timedelta

from tests.conftest import ONBOARDING, tool_reply
from tests.test_foods import CHICKEN, log_and_confirm


def register(client, email="me@example.com"):
    r = client.post("/api/auth/register", json={"email": email, "password": "password123", "consent": True})
    assert r.status_code == 201


def years_ago(n: int, extra_days: int = 0) -> str:
    today = date.today()
    try:
        d = today.replace(year=today.year - n)
    except ValueError:        # 29 February
        d = today.replace(year=today.year - n, day=28)
    return (d + timedelta(days=extra_days)).isoformat()


def onboard(client, dob: str):
    return client.post("/api/profile/onboarding", json={**ONBOARDING, "date_of_birth": dob, "timezone": "UTC"})


def test_adults_only(client):
    register(client)
    r = onboard(client, years_ago(17))
    assert r.status_code == 422 and "adults (18 and over)" in r.json()["detail"]
    assert onboard(client, years_ago(18, extra_days=1)).status_code == 422      # turns 18 tomorrow
    assert onboard(client, years_ago(18)).status_code == 200                    # 18th birthday today


def test_impossible_dates(client):
    register(client)
    tomorrow = (date.today() + timedelta(days=2)).isoformat()
    for dob in (tomorrow, years_ago(121)):
        r = onboard(client, dob)
        assert r.status_code == 422 and r.json()["detail"] == "Please check your date of birth"


def test_download_my_data(client, user, fake_llm):
    log_and_confirm(client, fake_llm, [CHICKEN])
    client.post("/api/water", json={"amount_ml": 500})
    r = client.get("/api/profile/export")
    assert r.status_code == 200
    assert r.headers["content-disposition"].startswith('attachment; filename="omniai-my-data-')
    data = r.json()
    assert data["account"]["email"] == "me@example.com"
    assert "hashed_password" not in data["account"] and "google_sub" not in data["account"]
    assert data["account"]["has_password"] is True
    assert data["food_log"][0]["items"][0]["ingredient_name"] == "chicken breast, cooked"
    assert data["water_logs"][0]["amount_ml"] == 500
    assert data["my_foods"][0]["name"] == "chicken breast, cooked"
    assert any(m["role"] == "user" for m in data["chat_messages"])
    assert data["weight_logs"] and data["targets"] and data["proposals"]


def test_export_only_has_your_own_data(client, user, fake_llm):
    log_and_confirm(client, fake_llm, [CHICKEN])
    client.post("/api/auth/logout")
    register(client, "other@example.com")
    data = client.get("/api/profile/export").json()     # not onboarded yet: still allowed
    assert data["account"]["email"] == "other@example.com"
    assert data["food_log"] == [] and data["my_foods"] == [] and data["chat_messages"] == []


def test_export_needs_login(client):
    assert client.get("/api/profile/export").status_code == 401
