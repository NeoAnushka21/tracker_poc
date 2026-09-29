"""Password hashing: Argon2id for new passwords; old scrypt hashes still work and are upgraded."""
import base64
import hashlib
import secrets

from app.db import SessionLocal
from app.models import User
from app.routers import auth as auth_router
from app.security import hash_password, needs_rehash, verify_password


def old_scrypt_hash(password: str) -> str:
    """Exactly how passwords were hashed before 2026-09-29."""
    salt = secrets.token_bytes(16)
    digest = hashlib.scrypt(password.encode(), salt=salt, n=2**14, r=8, p=1, dklen=64)
    return "scrypt$" + base64.b64encode(salt).decode() + "$" + base64.b64encode(digest).decode()


def stored_hash(email="me@example.com") -> str:
    with SessionLocal() as db:
        return db.query(User).filter_by(email=email).one().hashed_password


def test_new_passwords_use_argon2id_with_owasp_settings():
    h = hash_password("password123")
    assert h.startswith("$argon2id$v=19$m=19456,t=2,p=1$")
    assert verify_password("password123", h) and not verify_password("wrong", h)
    assert not needs_rehash(h)
    assert not verify_password("x", "") and not verify_password("x", "garbage")


def test_registration_stores_argon2id(client, user):
    assert stored_hash().startswith("$argon2id$")


def test_old_scrypt_hash_still_logs_in_and_is_upgraded(client, user):
    with SessionLocal() as db:
        u = db.query(User).filter_by(email="me@example.com").one()
        u.hashed_password = old_scrypt_hash("password123")
        db.commit()
    assert needs_rehash(stored_hash())
    client.post("/api/auth/logout")
    bad = client.post("/api/auth/login", json={"email": "me@example.com", "password": "wrong-one"})
    assert bad.status_code == 401 and stored_hash().startswith("scrypt$")      # not touched on failure
    ok = client.post("/api/auth/login", json={"email": "me@example.com", "password": "password123"})
    assert ok.status_code == 200 and stored_hash().startswith("$argon2id$")   # upgraded
    client.post("/api/auth/logout")
    assert client.post("/api/auth/login", json={"email": "me@example.com", "password": "password123"}).status_code == 200


def test_unknown_email_does_the_same_hashing_work(client, monkeypatch):
    calls = []
    monkeypatch.setattr(auth_router, "burn_verify_time", lambda pw: calls.append(pw))
    r = client.post("/api/auth/login", json={"email": "nobody@example.com", "password": "password123"})
    assert r.status_code == 401 and calls == ["password123"]
