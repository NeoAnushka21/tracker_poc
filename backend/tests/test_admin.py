"""Consent at sign-up, login tracking, and the read-only admin panel."""
import pytest

from app import config
from app.db import SessionLocal
from app.models import User
from tests.test_foods import CHICKEN, log_and_confirm


@pytest.fixture
def admin_emails(monkeypatch):
    monkeypatch.setattr(config, "ADMIN_EMAILS", {"boss@example.com"})
    monkeypatch.setattr(config, "ADMIN_INITIAL_PASSWORD", "boss-password-123")


def login_admin(client):
    from app.data_migrations import ensure_admin_accounts
    with SessionLocal() as db:
        ensure_admin_accounts(db)
    client.post("/api/auth/logout")
    r = client.post("/api/auth/admin-login", json={"email": "boss@example.com", "password": "boss-password-123"})
    assert r.status_code == 200, r.text
    return r.json()


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
    assert login_admin(client)["is_admin"] is True

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
    login_admin(client)
    assert client.get("/api/admin/users/999").status_code == 404


def test_default_admin_is_only_the_configured_email(client, user):
    # conftest's user is me@example.com; with the default config it must not be an admin.
    assert config.ADMIN_EMAILS == {"mhatre.anushka.work@gmail.com"}
    assert client.get("/api/auth/me").json()["is_admin"] is False
    assert client.get("/api/admin/users").status_code == 403
    assert client.get("/api/admin/audit").status_code == 403


# --- admin login separation ---

def test_admin_email_cannot_register_or_use_normal_login(client, admin_emails):
    r = client.post("/api/auth/register", json={"email": "boss@example.com", "password": "password123", "consent": True})
    assert r.status_code == 403 and "Admin login" in r.json()["detail"]
    login_admin(client)
    client.post("/api/auth/logout")
    r = client.post("/api/auth/login", json={"email": "boss@example.com", "password": "boss-password-123"})
    assert r.status_code == 403 and "Admin login" in r.json()["detail"]


def test_regular_user_cannot_use_admin_login(client, user, admin_emails):
    r = client.post("/api/auth/admin-login", json={"email": "me@example.com", "password": "password123"})
    assert r.status_code == 403


def test_admin_bootstrap_is_once_only(client, admin_emails, monkeypatch):
    from app.data_migrations import ensure_admin_accounts
    with SessionLocal() as db:
        assert ensure_admin_accounts(db) == ["boss@example.com"]
        monkeypatch.setattr(config, "ADMIN_INITIAL_PASSWORD", "something-else-999")
        assert ensure_admin_accounts(db) == []
    ok = client.post("/api/auth/admin-login", json={"email": "boss@example.com", "password": "boss-password-123"})
    assert ok.status_code == 200          # original password still works; not overwritten


# --- settings: account details, password, deletion ---

def test_account_details_in_me(client, user):
    me = client.get("/api/auth/me").json()
    assert me["email"] == "me@example.com" and me["created_at"] and me["last_login_at"] and me["consented_at"]


def test_change_password(client, user):
    bad = client.post("/api/auth/change-password", json={"current_password": "nope", "new_password": "newpassword1"})
    assert bad.status_code == 401
    ok = client.post("/api/auth/change-password", json={"current_password": "password123", "new_password": "newpassword1"})
    assert ok.status_code == 200
    client.post("/api/auth/logout")
    assert client.post("/api/auth/login", json={"email": "me@example.com", "password": "password123"}).status_code == 401
    assert client.post("/api/auth/login", json={"email": "me@example.com", "password": "newpassword1"}).status_code == 200


def test_delete_account_removes_everything(client, user, fake_llm):
    from tests.test_foods import ATTA, OIL, chat_propose
    from app.models import ChatMessage, LogEntry, UserFood, WaterLog, WeightLog, RecipeIngredient
    log_and_confirm(client, fake_llm, [CHICKEN])
    recipe = chat_propose(client, fake_llm, "propose_recipe", {
        "name": "Chapati", "ingredients": [ATTA, OIL], "yield_pieces": 4, "yield_servings": None, "cooked_weight_g": None})
    client.post(f"/api/actions/{recipe['id']}/confirm")
    client.post("/api/water", json={"amount_ml": 250})

    assert client.post("/api/auth/delete-account", json={"password": "wrong"}).status_code == 401
    assert client.post("/api/auth/delete-account", json={"password": "password123"}).status_code == 200
    assert client.get("/api/auth/me").status_code == 401
    with SessionLocal() as db:
        for model in (User, LogEntry, UserFood, WaterLog, WeightLog, ChatMessage, RecipeIngredient):
            assert db.query(model).count() == 0, model.__name__
    assert client.post("/api/auth/login", json={"email": "me@example.com", "password": "password123"}).status_code == 401


def test_admin_account_cannot_be_deleted(client, admin_emails):
    login_admin(client)
    r = client.post("/api/auth/delete-account", json={"password": "boss-password-123"})
    assert r.status_code == 403


def test_admin_accounts_are_not_listed_as_users(client, user, admin_emails):
    admin = login_admin(client)
    emails = [u["email"] for u in client.get("/api/admin/users").json()]
    assert emails == ["me@example.com"]
    assert client.get(f"/api/admin/users/{admin['id']}").status_code == 404
