"""Admin two-step sign-in (TOTP), shorter admin sessions, and the recovery script."""
import time

import jwt
import pyotp
import pytest

from app import config
from app.config import SECRET_KEY
from app.db import SessionLocal
from app.models import User
from app.security import hash_password

ADMIN = "mhatre.anushka.work@gmail.com"
PASSWORD = "admin-password-1"


@pytest.fixture
def admin(client):
    with SessionLocal() as db:
        db.add(User(email=ADMIN, hashed_password=hash_password(PASSWORD)))
        db.commit()
    r = client.post("/api/auth/admin-login", json={"email": ADMIN, "password": PASSWORD})
    assert r.status_code == 200
    return client


def code_for(secret: str, offset_steps: int = 0) -> str:
    return pyotp.TOTP(secret).at(int(time.time()) + offset_steps * 30)


def turn_on(client) -> str:
    setup = client.post("/api/admin/totp/setup").json()
    assert setup["uri"].startswith("otpauth://totp/") and setup["qr_svg_data_uri"].startswith("data:image/svg+xml")
    assert client.post("/api/admin/totp/enable", json={"code": code_for(setup["secret"])}).status_code == 200
    return setup["secret"]


def test_admin_sessions_last_12_hours(admin):
    token = admin.cookies.get("session")
    claims = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
    assert claims["exp"] - claims["iat"] == config.ADMIN_SESSION_HOURS * 3600


def test_setup_needs_a_correct_code_before_it_counts(admin):
    setup = admin.post("/api/admin/totp/setup").json()
    assert admin.post("/api/admin/totp/enable", json={"code": "000000"}).status_code == 400
    assert admin.get("/api/admin/totp").json() == {"enabled": False}
    admin.post("/api/auth/logout")
    # Not on yet: password alone still works.
    assert admin.post("/api/auth/admin-login", json={"email": ADMIN, "password": PASSWORD}).status_code == 200
    assert setup["secret"]


def test_login_needs_the_code_once_on(admin):
    secret = turn_on(admin)
    admin.post("/api/auth/logout")
    r = admin.post("/api/auth/admin-login", json={"email": ADMIN, "password": PASSWORD})
    assert r.status_code == 401 and r.json()["detail"] == "code_required"
    assert admin.get("/api/auth/me").status_code == 401
    bad = admin.post("/api/auth/admin-login", json={"email": ADMIN, "password": PASSWORD, "code": "123456"})
    assert bad.status_code == 401 and "isn't right" in bad.json()["detail"]
    ok = admin.post("/api/auth/admin-login", json={"email": ADMIN, "password": PASSWORD, "code": code_for(secret, 1)})
    assert ok.status_code == 200 and admin.get("/api/auth/me").json()["is_admin"]


def test_a_code_works_only_once(admin):
    secret = turn_on(admin)
    admin.post("/api/auth/logout")
    code = code_for(secret, 1)
    body = {"email": ADMIN, "password": PASSWORD, "code": code}
    assert admin.post("/api/auth/admin-login", json=body).status_code == 200
    admin.post("/api/auth/logout")
    assert admin.post("/api/auth/admin-login", json=body).status_code == 401    # replay refused


def test_wrong_password_never_reaches_the_code_step(admin):
    turn_on(admin)
    admin.post("/api/auth/logout")
    r = admin.post("/api/auth/admin-login", json={"email": ADMIN, "password": "wrong-pass", "code": "123456"})
    assert r.status_code == 401 and r.json()["detail"] == "Wrong email or password"


def test_turning_it_off_needs_password_and_code(admin):
    secret = turn_on(admin)
    assert admin.post("/api/admin/totp/disable", json={"password": PASSWORD, "code": "000000"}).status_code == 401
    ok = admin.post("/api/admin/totp/disable", json={"password": PASSWORD, "code": code_for(secret, 1)})
    assert ok.status_code == 200 and admin.get("/api/admin/totp").json() == {"enabled": False}
    audit = [a["action"] for a in admin.get("/api/admin/audit").json()]
    assert "two-step sign-in turned on" in audit and "two-step sign-in turned off" in audit


def test_secret_is_stored_encrypted(admin):
    secret = turn_on(admin)
    with SessionLocal() as db:
        stored = db.query(User).filter_by(email=ADMIN).one().totp_secret
    assert secret not in stored


def test_recovery_script_turns_it_off(admin):
    turn_on(admin)
    from scripts.reset_admin_2fa import main
    main(ADMIN)
    admin.post("/api/auth/logout")
    assert admin.post("/api/auth/admin-login", json={"email": ADMIN, "password": PASSWORD}).status_code == 200


def test_normal_users_cant_use_it(client, user):
    assert client.post("/api/admin/totp/setup").status_code == 403
