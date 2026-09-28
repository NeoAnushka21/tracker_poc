"""Body profile: height updates, optional dated measurements, BMI and the body-fat estimate."""
import pytest

from app.db import SessionLocal
from app.models import BodyMeasurement


def test_body_profile_starts_with_weight_and_height_only(client, user):
    body = client.get("/api/profile/body").json()
    assert (body["height_cm"], body["weight_kg"]) == (180, 80)
    assert all(p["value_cm"] is None for p in body["latest"])
    assert [p["label"] for p in body["latest"]] == [
        "Neck", "Shoulders", "Chest", "Biceps", "Forearm", "Wrist", "Waist", "Hips", "Thigh", "Calf"]
    assert all(p["tip"] for p in body["latest"])                       # how to measure each one
    # With no measurements at all, weight, height and BMI still show; body fat says what's missing.
    assert body["bmi"] == {"status": "ok", "value": 24.7, "category": "Healthy weight",
                           "note": "WHO adult categories. BMI doesn't tell muscle from fat."}
    assert body["body_fat"]["status"] == "missing" and body["body_fat"]["missing"] == ["neck", "waist"]


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



# --- BMI (WHO adult categories) --------------------------------------------------

@pytest.mark.parametrize("kg,cm,value,category", [
    (50, 170, 17.3, "Underweight"), (53.5, 170, 18.5, "Healthy weight"),   # 18.5 is healthy
    (72, 175, 23.5, "Healthy weight"), (76.6, 175, 25.0, "Overweight"),
    (95, 178, 30.0, "Obesity"),                                          # 29.98 shows as 30.0
])
def test_bmi_categories(kg, cm, value, category):
    from app.services.body import bmi
    r = bmi(kg, cm)
    assert (r["value"], r["category"]) == (value, category)


def test_bmi_needs_weight_and_height():
    from app.services.body import bmi
    assert bmi(None, 170) == {"status": "missing", "missing": ["weight"]}


# --- body fat: US Navy equations ---------------------------------------------------

def test_navy_male_and_female_match_the_published_equations():
    import math
    from app.services.body import body_fat_navy
    male = body_fat_navy("male", 178, 38, 86, None)
    expected = 495 / (1.0324 - 0.19077 * math.log10(86 - 38) + 0.15456 * math.log10(178)) - 450
    assert male["status"] == "ok" and male["value"] == round(expected, 1) == 17.2
    female = body_fat_navy("female", 165, 33, 72, 98)
    expected = 495 / (1.29579 - 0.35004 * math.log10(72 + 98 - 33) + 0.22100 * math.log10(165)) - 450
    assert female["status"] == "ok" and female["value"] == round(expected, 1) == 26.9
    assert "US Navy" in male["method"] and male["typical_error"] == 3.5


def test_navy_says_what_is_missing_instead_of_guessing():
    from app.services.body import body_fat_navy
    assert body_fat_navy("male", 178, None, 86, None)["missing"] == ["neck"]
    assert body_fat_navy("female", 165, 33, 72, None)["missing"] == ["hips"]      # women also need hips
    assert body_fat_navy("male", 178, 38, 86, None).get("missing") is None         # men don't
    assert body_fat_navy(None, 178, 38, 86, 90)["missing"] == ["sex (in your profile)"]


@pytest.mark.parametrize("args", [
    ("male", 178, 40, 38, None),       # waist smaller than neck
    ("male", 178, 38, 40, None),       # result far below the human range
    ("female", 165, 33, 250, 250),     # result above the range
])
def test_navy_refuses_implausible_measurements(args):
    from app.services.body import body_fat_navy
    r = body_fat_navy(*args)
    assert r["status"] == "implausible" and "value" not in r and r["reason"]


def test_profile_estimates_body_fat_from_the_latest_measurements(client, user):
    client.post("/api/profile/measurements", json={"neck_cm": 38, "waist_cm": 90})
    body = client.post("/api/profile/measurements", json={"waist_cm": 86, "shoulders_cm": 118, "wrist_cm": 17}).json()
    fat = body["body_fat"]
    import math
    expected = 495 / (1.0324 - 0.19077 * math.log10(86 - 38) + 0.15456 * math.log10(180)) - 450
    assert fat["status"] == "ok" and fat["value"] == round(expected, 1) and "warning" not in fat
    latest = {p["key"]: p["value_cm"] for p in body["latest"]}
    assert (latest["shoulders_cm"], latest["wrist_cm"]) == (118, 17)


def test_measurements_months_apart_get_a_warning(client, user):
    from datetime import timedelta
    client.post("/api/profile/measurements", json={"neck_cm": 38})
    with SessionLocal() as db:
        m = db.query(BodyMeasurement).one()
        m.measured_at -= timedelta(days=60)
        db.commit()
    fat = client.post("/api/profile/measurements", json={"waist_cm": 86}).json()["body_fat"]
    assert fat["status"] == "ok" and "month" in fat["warning"]


# --- correcting a saved set -----------------------------------------------------------

def test_edit_a_saved_set(client, user):
    body = client.post("/api/profile/measurements", json={"chest_cm": 59, "waist_cm": 80}).json()   # typo: 59
    mid = body["history"][0]["id"]
    body = client.put(f"/api/profile/measurements/{mid}", json={"chest_cm": 95, "waist_cm": 80}).json()
    assert body["history"][0]["chest_cm"] == 95 and len(body["history"]) == 1     # corrected, not added
    body = client.put(f"/api/profile/measurements/{mid}", json={"chest_cm": 95}).json()
    assert body["history"][0]["waist_cm"] is None                                   # cleared
    assert client.put(f"/api/profile/measurements/{mid}", json={}).status_code == 422
    assert client.put("/api/profile/measurements/999999", json={"chest_cm": 90}).status_code == 404
