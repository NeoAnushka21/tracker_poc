"""Body profile: height updates and optional dated measurements."""
from app.db import SessionLocal
from app.models import BodyMeasurement


def test_body_profile_starts_with_weight_and_height_only(client, user):
    body = client.get("/api/profile/body").json()
    assert (body["height_cm"], body["weight_kg"]) == (180, 80)
    assert all(p["value_cm"] is None for p in body["latest"])
    assert [p["label"] for p in body["latest"]][:4] == ["Neck", "Chest", "Waist", "Hips"]


def test_measurements_are_optional_and_track_change(client, user):
    assert client.post("/api/profile/measurements", json={}).status_code == 422
    assert client.post("/api/profile/measurements", json={"waist_cm": 5}).status_code == 422   # out of range
    client.post("/api/profile/measurements", json={"waist_cm": 80, "biceps_cm": 33})
    body = client.post("/api/profile/measurements", json={"waist_cm": 78.4}).json()
    latest = {p["key"]: p for p in body["latest"]}
    assert (latest["waist_cm"]["value_cm"], latest["waist_cm"]["change_cm"]) == (78.4, -1.6)
    assert (latest["biceps_cm"]["value_cm"], latest["biceps_cm"]["change_cm"]) == (33, None)   # only one reading
    assert len(body["history"]) == 2


def test_delete_measurement_only_own(client, user):
    from tests.conftest import make_user
    body = client.post("/api/profile/measurements", json={"chest_cm": 95}).json()
    mid = body["history"][0]["id"]
    client.post("/api/auth/logout")
    make_user(client, "other@example.com")
    assert client.delete(f"/api/profile/measurements/{mid}").status_code == 404
    client.post("/api/auth/logout")
    client.post("/api/auth/login", json={"email": "me@example.com", "password": "password123"})
    assert client.delete(f"/api/profile/measurements/{mid}").json()["history"] == []


def test_height_update_can_recalculate_targets(client, user):
    before = client.get("/api/auth/me").json()["targets"]["calories"]
    u = client.post("/api/profile/height", json={"height_cm": 190, "recalculate_targets": True}).json()
    assert u["height_cm"] == 190 and u["targets"]["calories"] > before
    u = client.post("/api/profile/height", json={"height_cm": 170, "recalculate_targets": False}).json()
    assert u["height_cm"] == 170 and u["targets"]["calories"] > before       # targets unchanged this time


def test_account_deletion_removes_measurements(client, user):
    client.post("/api/profile/measurements", json={"calf_cm": 36})
    client.post("/api/auth/delete-account", json={"password": "password123"})
    with SessionLocal() as db:
        assert db.query(BodyMeasurement).count() == 0
