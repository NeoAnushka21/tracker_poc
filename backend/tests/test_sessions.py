"""Sessions can be ended: a password change signs out other devices; Log out everywhere ends all."""
import jwt
from fastapi.testclient import TestClient

from app.config import SECRET_KEY
from app.main import app

LOGIN = {"email": "me@example.com", "password": "password123"}


def second_device() -> TestClient:
    other = TestClient(app)
    assert other.post("/api/auth/login", json=LOGIN).status_code == 200
    return other


def test_password_change_signs_out_other_devices_only(client, user):
    phone = second_device()
    assert phone.get("/api/auth/me").status_code == 200
    r = client.post("/api/auth/change-password", json={"current_password": "password123", "new_password": "newpass456"})
    assert r.status_code == 200
    assert client.get("/api/auth/me").status_code == 200          # this browser got a fresh cookie
    assert phone.get("/api/auth/me").status_code == 401           # the other device is out


def test_log_out_everywhere(client, user):
    phone = second_device()
    assert client.post("/api/auth/logout-everywhere").status_code == 200
    assert client.get("/api/auth/me").status_code == 401
    assert phone.get("/api/auth/me").status_code == 401
    assert second_device().get("/api/auth/me").status_code == 200  # logging in again works


def test_a_copied_cookie_stops_working_after_log_out_everywhere(client, user):
    stolen = client.cookies.get("session")
    thief = TestClient(app)
    thief.cookies.set("session", stolen)
    assert thief.get("/api/auth/me").status_code == 200
    second_device().post("/api/auth/logout-everywhere")
    assert thief.get("/api/auth/me").status_code == 401


def test_tokens_from_before_versions_still_work(client, user):
    """Cookies issued before this change carry no version: they count as version 0."""
    uid = client.get("/api/auth/me").json()["id"]
    old = jwt.encode({"sub": str(uid), "iat": 1, "exp": 4102444800}, SECRET_KEY, algorithm="HS256")
    legacy = TestClient(app)
    legacy.cookies.set("session", old)
    assert legacy.get("/api/auth/me").status_code == 200
