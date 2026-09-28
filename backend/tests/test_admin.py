"""Consent at sign-up, login tracking, and the read-only admin panel."""
import pytest

from app import config
from app.db import SessionLocal
from app.models import User
from tests.conftest import make_user
from tests.test_foods import CHICKEN, log_and_confirm


@pytest.fixture
def admin_emails(monkeypatch):
    monkeypatch.setattr(config, "ADMIN_EMAILS", {"boss@example.com"})


def test_register_requires_consent(client):
    r = client.post("/api/auth/register", json={"email": "a@example.com", "password": "password123"})
    assert r.status_code == 422 and "consent" in r.json()["detail"]
    assert client.get("/api/auth/consent-text").json()["version"] == config.CONSENT_VERSION


def test_existing_user_without_consent_must_accept(client, user):
    with SessionLocal() as db:
        db.get(User, user["id"]).consent_version = None
        db.commit()
    assert client.get("/api/auth/me").json()["consented"] is False
    assert client.get("/api/dashboard/daily").status_code == 403
    assert client.post("/api/auth/consent").json()["consented"] is True
    assert client.get("/api/dashboard/daily").status_code == 200


def test_logins_are_counted(client, user):
    client.post("/api/auth/logout")
    client.post("/api/auth/login", json={"email": "me@example.com", "password": "password123"})
    with SessionLocal() as db:
        u = db.get(User, user["id"])
        assert u.login_count == 2 and u.last_login_at is not None


def test_non_admins_are_refused(client, user, admin_emails):
    assert client.get("/api/auth/me").json()["is_admin"] is False
    assert client.get("/api/admin/users").status_code == 403


def test_admin_sees_users_and_their_data_and_is_audited(client, user, fake_llm, admin_emails):
    log_and_confirm(client, fake_llm, [CHICKEN])
    client.post("/api/water", json={"amount_ml": 500})
    client.post("/api/auth/logout")
    make_user(client, "boss@example.com")
    assert client.get("/api/auth/me").json()["is_admin"] is True

    users = {u["email"]: u for u in client.get("/api/admin/users").json()}
    me = users["me@example.com"]
    assert (me["entries"], me["foods"], me["water_logs"], me["chat_messages"]) == (1, 1, 1, 1)
    assert me["consented_at"] and me["last_login_at"]

    detail = client.get(f"/api/admin/users/{me['id']}").json()
    assert detail["profile"]["email"] == "me@example.com"
    assert detail["days"][0]["entries"][0]["items"][0]["ingredient_name"] == "chicken breast, cooked"
    assert [f["name"] for f in detail["foods"]] == ["chicken breast, cooked"]
    assert client.get(f"/api/admin/users/{me['id']}/chat").json()[0]["role"] == "user"

    actions = [a["action"] for a in client.get("/api/admin/audit").json()]
    assert {"list_users", "view_user_chat"} <= set(actions)
    assert any(a.startswith("view_user_detail") for a in actions)


def test_admin_unknown_user_404(client, user, admin_emails):
    client.post("/api/auth/logout")
    make_user(client, "boss@example.com")
    assert client.get("/api/admin/users/999").status_code == 404


def test_default_admin_is_only_the_configured_email(client, user):
    # conftest's user is me@example.com; with the default config it must not be an admin.
    assert config.ADMIN_EMAILS == {"mhatre.anushka.work@gmail.com"}
    assert client.get("/api/auth/me").json()["is_admin"] is False
    assert client.get("/api/admin/users").status_code == 403
    assert client.get("/api/admin/audit").status_code == 403
