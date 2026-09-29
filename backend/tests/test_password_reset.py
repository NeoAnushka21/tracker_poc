"""Forgot password: same reply for every email, one-time links, expiry, sign-out everywhere."""
import re
from datetime import timedelta

import pytest
from fastapi.testclient import TestClient

from app import config
from app.db import SessionLocal
from app.main import app
from app.models import PasswordReset
from app.services import email

LOGIN = {"email": "me@example.com", "password": "password123"}


@pytest.fixture
def outbox(monkeypatch):
    sent = []
    monkeypatch.setattr(email, "send", lambda to, subject, text: sent.append({"to": to, "subject": subject, "text": text}))
    monkeypatch.setattr(config, "PUBLIC_APP_URL", "https://omniai.example")
    return sent


def forgot(client, addr="me@example.com"):
    return client.post("/api/auth/forgot-password", json={"email": addr})


def token_from(mail: dict) -> str:
    return re.search(r"/reset-password#token=([\w-]+)", mail["text"]).group(1)


def test_same_reply_whether_or_not_the_account_exists(client, user, outbox):
    known, unknown = forgot(client), forgot(client, "nobody@example.com")
    assert known.status_code == unknown.status_code == 200 and known.json() == unknown.json()
    assert [m["to"] for m in outbox] == ["me@example.com"]
    assert outbox[0]["text"].count("https://omniai.example/reset-password#token=") == 1   # fixed address, token after #


def test_reset_sets_the_password_and_signs_out_everywhere(client, user, outbox):
    phone = TestClient(app)
    phone.post("/api/auth/login", json=LOGIN)
    forgot(client)
    r = client.post("/api/auth/reset-password", json={"token": token_from(outbox[0]), "new_password": "brandnew789"})
    assert r.status_code == 200
    assert phone.get("/api/auth/me").status_code == 401 and client.get("/api/auth/me").status_code == 401
    assert client.post("/api/auth/login", json=LOGIN).status_code == 401
    assert client.post("/api/auth/login", json={**LOGIN, "password": "brandnew789"}).status_code == 200


def test_links_work_once_and_a_new_one_replaces_the_old(client, user, outbox):
    forgot(client), forgot(client)
    first, second = token_from(outbox[0]), token_from(outbox[1])
    bad = client.post("/api/auth/reset-password", json={"token": first, "new_password": "brandnew789"})
    assert bad.status_code == 400 and "expired or was already used" in bad.json()["detail"]
    assert client.post("/api/auth/reset-password", json={"token": second, "new_password": "brandnew789"}).status_code == 200
    assert client.post("/api/auth/reset-password", json={"token": second, "new_password": "again12345"}).status_code == 400


def test_links_expire(client, user, outbox):
    forgot(client)
    with SessionLocal() as db:
        row = db.query(PasswordReset).one()
        row.expires_at = row.created_at - timedelta(minutes=1)
        db.commit()
    r = client.post("/api/auth/reset-password", json={"token": token_from(outbox[0]), "new_password": "brandnew789"})
    assert r.status_code == 400
    assert client.post("/api/auth/reset-password", json={"token": "x" * 43, "new_password": "brandnew789"}).status_code == 400


def test_only_a_hash_of_the_token_is_stored(client, user, outbox):
    forgot(client)
    with SessionLocal() as db:
        stored = db.query(PasswordReset).one().token_hash
    assert token_from(outbox[0]) not in stored and len(stored) == 64


def test_reset_emails_are_limited_per_address(client, user, outbox, monkeypatch):
    monkeypatch.setattr(config, "PASSWORD_RESETS_PER_EMAIL", 2)
    assert [forgot(client).status_code for _ in range(3)] == [200, 200, 429]
    assert len(outbox) == 2


def test_admin_account_isnt_reset_by_email(client, outbox):
    assert forgot(client, "mhatre.anushka.work@gmail.com").status_code == 200
    assert outbox == []


def test_off_in_production_without_an_email_service(client, monkeypatch):
    monkeypatch.setattr(config, "COOKIE_SECURE", True)
    monkeypatch.setattr(config, "BREVO_API_KEY", "")
    assert client.get("/api/auth/options").json()["password_reset"] is False
    assert forgot(client).status_code == 503


def test_development_prints_the_link_instead_of_sending(caplog, monkeypatch):
    monkeypatch.setattr(config, "BREVO_API_KEY", "")
    with caplog.at_level("INFO", logger="omniai.email"):
        email.send("me@example.com", "Subject", "https://example/reset-password#token=abc")
    assert "reset-password#token=abc" in caplog.text
    assert email.enabled() is True
