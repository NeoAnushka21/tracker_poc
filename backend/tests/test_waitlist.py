"""The waitlist (2026-10-01): the welcome page's "Join the community" form, the admin's Waitlist
list with Approve / Remove, and the invite-only gate on new accounts while JOIN_MODE is "waitlist"."""
import pytest
from sqlalchemy import select

from app import config
from app.db import SessionLocal
from app.models import WaitlistEntry, utcnow
from app.services import email
from tests.test_admin import admin_emails, login_admin  # noqa: F401  (fixture)
from tests.test_google_auth import google, google_configured, token  # noqa: F401  (fixture)

LAUNCHER = "https://launcher.example.com"
FORM = {"name": "Asha  Rao", "email": " Asha@Example.com ", "interest": "protein, weight loss", "consent": True}


@pytest.fixture
def sent(monkeypatch):
    mails: list[dict] = []
    monkeypatch.setattr(email, "send", lambda to, subject, text: mails.append({"to": to, "subject": subject, "text": text}))
    return mails


@pytest.fixture
def waitlist_mode(monkeypatch):
    monkeypatch.setattr(config, "JOIN_MODE", "waitlist")
    monkeypatch.setattr(config, "LAUNCHER_ORIGIN", LAUNCHER)


def rows() -> list[WaitlistEntry]:
    with SessionLocal() as db:
        return list(db.scalars(select(WaitlistEntry)))


def register(client, email_address="asha@example.com"):
    return client.post("/api/auth/register", json={"email": email_address, "password": "password123", "consent": True})


def test_options_report_the_join_mode(client, waitlist_mode):
    assert client.get("/api/waitlist/options").json() == {"join_mode": "waitlist"}
    assert client.get("/api/auth/options").json()["join_mode"] == "waitlist"


def test_join_stores_the_person_and_alerts_the_admin(client, waitlist_mode, sent):
    r = client.post("/api/waitlist", json=FORM)
    assert r.status_code == 200 and r.json() == {"ok": True}
    [entry] = rows()
    assert (entry.email, entry.name, entry.interest, entry.approved_at) == ("asha@example.com", "Asha Rao", "protein, weight loss", None)
    [mail] = sent
    assert mail["to"] == config.WAITLIST_ALERT_EMAIL
    assert "Asha Rao <asha@example.com>" in mail["text"] and "People waiting now: 1" in mail["text"]


def test_joining_twice_or_with_an_account_adds_nothing_and_says_the_same(client, waitlist_mode, sent, monkeypatch):
    client.post("/api/waitlist", json=FORM)
    again = client.post("/api/waitlist", json={**FORM, "name": "Someone else"})
    assert again.json() == {"ok": True} and len(rows()) == 1 and rows()[0].name == "Asha Rao" and len(sent) == 1

    monkeypatch.setattr(config, "JOIN_MODE", "open")
    assert register(client, "member@example.com").status_code == 201
    member = client.post("/api/waitlist", json={**FORM, "email": "member@example.com"})
    assert member.json() == {"ok": True} and len(rows()) == 1


def test_form_checks(client, waitlist_mode, sent):
    no_consent = client.post("/api/waitlist", json={**FORM, "consent": False})
    assert no_consent.status_code == 422 and "tick" in no_consent.json()["detail"]
    assert client.post("/api/waitlist", json={**FORM, "email": "not-an-email"}).status_code == 422
    assert client.post("/api/waitlist", json={**FORM, "name": "   "}).status_code == 422
    # A bot fills in the hidden field: it's told "ok", and nothing is stored or sent.
    assert client.post("/api/waitlist", json={**FORM, "website": "http://spam"}).json() == {"ok": True}
    assert rows() == [] and sent == []


def test_form_sends_are_rate_limited_per_address(client, waitlist_mode, sent):
    for i in range(config.WAITLIST_REQUESTS_PER_IP):
        assert client.post("/api/waitlist", json={**FORM, "email": f"p{i}@example.com"}).status_code == 200
    r = client.post("/api/waitlist", json={**FORM, "email": "one-more@example.com"}, headers={"Origin": LAUNCHER})
    assert r.status_code == 429
    assert r.headers["access-control-allow-origin"] == LAUNCHER     # the other site can read the reason


def test_only_the_launcher_origin_gets_cors_and_only_on_the_waitlist(client, waitlist_mode, sent):
    pre = client.options("/api/waitlist", headers={"Origin": LAUNCHER, "Access-Control-Request-Method": "POST"})
    assert pre.status_code == 204 and pre.headers["access-control-allow-origin"] == LAUNCHER
    assert "POST" in pre.headers["access-control-allow-methods"]
    ok = client.post("/api/waitlist", json=FORM, headers={"Origin": LAUNCHER})
    assert ok.headers["access-control-allow-origin"] == LAUNCHER
    assert "access-control-allow-credentials" not in ok.headers
    other = client.post("/api/waitlist", json={**FORM, "email": "b@example.com"}, headers={"Origin": "https://evil.example"})
    assert "access-control-allow-origin" not in other.headers
    elsewhere = client.get("/api/auth/options", headers={"Origin": LAUNCHER})
    assert "access-control-allow-origin" not in elsewhere.headers


def test_open_mode_lets_anyone_sign_up(client):
    assert config.JOIN_MODE == "open"
    assert register(client).status_code == 201


def test_waitlist_mode_blocks_new_accounts_until_approved(client, waitlist_mode, sent, admin_emails):  # noqa: F811
    blocked = register(client)
    assert blocked.status_code == 403 and "invite-only" in blocked.json()["detail"]
    client.post("/api/waitlist", json=FORM)
    assert register(client).status_code == 403                # on the list, not approved yet

    login_admin(client)
    listing = client.get("/api/admin/waitlist").json()
    assert listing["join_mode"] == "waitlist"
    [row] = listing["entries"]
    assert row["email"] == "asha@example.com" and row["approved_at"] is None and row["has_account"] is False
    approved = client.post(f"/api/admin/waitlist/{row['id']}/approve").json()
    assert approved["approved_at"] is not None
    invite = sent[-1]
    assert invite["to"] == "asha@example.com" and "Hi Asha Rao" in invite["text"] and f"{LAUNCHER}/#signup" in invite["text"]

    client.post("/api/auth/logout")
    assert register(client).status_code == 201
    login_admin(client)
    assert client.get("/api/admin/waitlist").json()["entries"][0]["has_account"] is True


def test_existing_accounts_still_log_in_in_waitlist_mode(client, monkeypatch):
    assert register(client).status_code == 201
    client.post("/api/auth/logout")
    monkeypatch.setattr(config, "JOIN_MODE", "waitlist")
    r = client.post("/api/auth/login", json={"email": "asha@example.com", "password": "password123"})
    assert r.status_code == 200


def test_google_new_account_needs_an_invite(client, waitlist_mode, sent, google_configured):  # noqa: F811
    r = google(client, token(email="asha@example.com"))
    assert r.status_code == 403 and "invite-only" in r.json()["detail"]
    client.post("/api/waitlist", json=FORM)
    with SessionLocal() as db:
        db.scalars(select(WaitlistEntry)).one().approved_at = utcnow()
        db.commit()
    assert google(client, token(email="asha@example.com")).json()["status"] == "consent_required"


def test_admin_can_remove_someone(client, waitlist_mode, sent, admin_emails):  # noqa: F811
    client.post("/api/waitlist", json=FORM)
    login_admin(client)
    [row] = client.get("/api/admin/waitlist").json()["entries"]
    assert client.delete(f"/api/admin/waitlist/{row['id']}").json() == {"ok": True}
    assert rows() == []
    assert client.delete(f"/api/admin/waitlist/{row['id']}").status_code == 404


def test_waitlist_is_admin_only(client, user):
    assert client.get("/api/admin/waitlist").status_code == 403


def test_deleting_an_account_removes_its_waitlist_row(client, waitlist_mode, sent):
    client.post("/api/waitlist", json=FORM)
    with SessionLocal() as db:
        db.scalars(select(WaitlistEntry)).one().approved_at = utcnow()
        db.commit()
    assert register(client).status_code == 201
    assert client.post("/api/auth/delete-account", json={"password": "password123"}).json() == {"ok": True}
    assert rows() == []

