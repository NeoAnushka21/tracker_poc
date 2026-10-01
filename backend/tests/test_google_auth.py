"""Continue with Google: token checks, new accounts need consent, linking needs the user's OK,
and accounts without a password can set one and delete themselves."""
import time
from types import SimpleNamespace

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa

from app import google_auth
from app.routers import auth as auth_router
from tests.conftest import ONBOARDING

CLIENT_ID = "test-client.apps.googleusercontent.com"
_KEY = rsa.generate_private_key(public_exponent=65537, key_size=2048)
_OTHER_KEY = rsa.generate_private_key(public_exponent=65537, key_size=2048)


@pytest.fixture(autouse=True)
def google_configured(monkeypatch):
    monkeypatch.setattr(google_auth, "GOOGLE_CLIENT_ID", CLIENT_ID)
    monkeypatch.setattr(auth_router, "GOOGLE_CLIENT_ID", CLIENT_ID)
    # Stand-in for Google's public keys: our test key, so the real signature check runs.
    monkeypatch.setattr(google_auth, "_jwks", SimpleNamespace(
        get_signing_key_from_jwt=lambda _token: SimpleNamespace(key=_KEY.public_key())))


def token(email="new@example.com", sub="g-123", key=_KEY, **overrides) -> str:
    now = int(time.time())
    claims = {"iss": "https://accounts.google.com", "aud": CLIENT_ID, "sub": sub, "email": email,
              "email_verified": True, "given_name": "Asha", "iat": now, "exp": now + 3600, **overrides}
    return jwt.encode(claims, key, algorithm="RS256")


def google(client, credential: str, **flags):
    return client.post("/api/auth/google", json={"credential": credential, **flags})


def test_options_show_the_client_id(client):
    assert client.get("/api/auth/options").json()["google_client_id"] == CLIENT_ID


def test_new_account_needs_consent_then_onboards(client):
    r = google(client, token())
    assert r.json() == {"status": "consent_required", "email": "new@example.com"}
    assert client.get("/api/auth/me").status_code == 401          # no session yet

    r = google(client, token(), consent=True)
    body = r.json()
    assert r.status_code == 200 and body["status"] == "ok"
    user = body["user"]
    assert user["email"] == "new@example.com" and user["consented"] and not user["onboarded"]
    assert user["has_password"] is False and user["google_linked"] is True
    assert user["preferred_name"] == "Asha"
    assert client.post("/api/profile/onboarding", json=ONBOARDING).status_code == 200

    client.post("/api/auth/logout")
    r = google(client, token())                                    # next time: straight in
    assert r.json()["status"] == "ok" and r.json()["user"]["onboarded"]


def test_existing_email_account_links_only_with_ok(client, user):
    r = google(client, token(email="me@example.com"))
    assert r.json() == {"status": "link_required", "email": "me@example.com"}
    assert client.get("/api/auth/me").status_code == 200          # the earlier session, untouched
    client.post("/api/auth/logout")

    r = google(client, token(email="me@example.com"), link=True)
    u = r.json()["user"]
    assert u["email"] == "me@example.com" and u["google_linked"] and u["has_password"]
    client.post("/api/auth/logout")
    # Both ways in now work.
    assert google(client, token(email="me@example.com")).json()["status"] == "ok"
    assert client.post("/api/auth/login", json={"email": "me@example.com", "password": "password123"}).status_code == 200


def test_bad_tokens_are_refused(client):
    for bad in (token(key=_OTHER_KEY), token(aud="someone-else"), token(exp=int(time.time()) - 10),
                token(iss="https://evil.example.com"), token(email_verified=False), "not-a-token" * 3):
        r = google(client, bad, consent=True)
        assert r.status_code == 401, bad
    assert client.get("/api/auth/me").status_code == 401


def test_admin_email_must_use_admin_login(client):
    r = google(client, token(email="mhatre.anushka.work@gmail.com"), consent=True)
    assert r.status_code == 403


def test_not_configured(client, monkeypatch):
    monkeypatch.setattr(auth_router, "GOOGLE_CLIENT_ID", "")
    assert client.get("/api/auth/options").json()["google_client_id"] is None
    assert google(client, token(), consent=True).status_code == 503


def test_google_only_account_password_and_delete(client):
    google(client, token(), consent=True)
    # A password login explains the account uses Google.
    client.post("/api/auth/logout")
    r = client.post("/api/auth/login", json={"email": "new@example.com", "password": "whatever123"})
    assert r.status_code == 401 and "Continue with Google" in r.json()["detail"]

    google(client, token())
    assert client.post("/api/auth/change-password", json={"new_password": "brandnew123"}).status_code == 200
    me = client.get("/api/auth/me").json()
    assert me["has_password"] is True
    client.post("/api/auth/logout")
    assert client.post("/api/auth/login", json={"email": "new@example.com", "password": "brandnew123"}).status_code == 200


def test_google_only_account_deletes_by_typing_email(client):
    google(client, token(), consent=True)
    assert client.post("/api/auth/delete-account", json={"confirm_email": "wrong@example.com"}).status_code == 401
    assert client.post("/api/auth/delete-account", json={"confirm_email": "New@Example.com"}).status_code == 200
    assert google(client, token()).json()["status"] == "consent_required"   # gone: would be a new account


def test_password_accounts_still_need_their_password(client, user):
    assert client.post("/api/auth/change-password", json={"new_password": "brandnew123"}).status_code == 401
    assert client.post("/api/auth/delete-account", json={"confirm_email": "me@example.com"}).status_code == 401


def test_google_only_account_can_set_a_password_by_reset_link(client, monkeypatch):
    import re
    from app import config
    from app.services import email
    sent = []
    monkeypatch.setattr(email, "send", lambda to, subject, text: sent.append(text))
    monkeypatch.setattr(config, "PUBLIC_APP_URL", "https://tandurust.example")
    google(client, token(), consent=True)
    client.post("/api/auth/logout")
    client.post("/api/auth/forgot-password", json={"email": "new@example.com"})
    reset = re.search(r"#token=([\w-]+)", sent[0]).group(1)
    assert client.post("/api/auth/reset-password", json={"token": reset, "new_password": "brandnew789"}).status_code == 200
    assert client.post("/api/auth/login", json={"email": "new@example.com", "password": "brandnew789"}).status_code == 200
