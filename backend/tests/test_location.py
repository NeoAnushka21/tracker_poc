"""Country (required) and region (optional) in the profile, from the dropdown lists only."""
from sqlalchemy import select

from app.db import SessionLocal
from app.models import User
from app.nutrition import age_on
from app.timeutil import local_today
from tests.conftest import ONBOARDING, internal_id
from tests.test_admin import admin_emails, login_admin  # noqa: F401  (fixture)


def register(client, email="new@example.com"):
    assert client.post("/api/auth/register", json={"email": email, "password": "password123",
                                                   "consent": True}).status_code == 201


def test_country_list_is_public_and_cached(client):
    r = client.get("/api/profile/countries")
    assert r.status_code == 200 and "max-age" in r.headers["cache-control"]
    india = next(c for c in r.json() if c["code"] == "IN")
    assert india["name"] == "India" and len(india["regions"]) == 36 and "Maharashtra" in india["regions"]
    assert len(r.json()) > 240


def test_onboarding_needs_a_country_from_the_list(client):
    register(client)
    no_country = {k: v for k, v in ONBOARDING.items() if k not in ("country", "region")}
    assert client.post("/api/profile/onboarding", json=no_country).status_code == 422
    for bad in ({"country": "XX"}, {"country": "IN", "region": "Texas"}, {"country": "IN", "region": "maharashtra"}):
        r = client.post("/api/profile/onboarding", json={**ONBOARDING, **bad})
        assert r.status_code == 422 and "from the list" in r.json()["detail"], bad
    me = client.post("/api/profile/onboarding", json={**ONBOARDING, "country": "in", "region": None}).json()
    assert (me["country"], me["country_name"], me["region"]) == ("IN", "India", None)   # region is optional
    assert me["needs_location"] is False


def test_age_comes_from_the_date_of_birth(client, user):
    me = client.get("/api/auth/me").json()
    assert me["age"] == age_on(__import__("datetime").date(1995, 6, 15), local_today("Asia/Kolkata"))


def test_existing_accounts_are_asked_once(client, user):
    with SessionLocal() as db:                                   # an account from before country was asked
        u = db.get(User, internal_id(user["id"]))
        u.country = u.region = None
        db.commit()
    assert client.get("/api/auth/me").json()["needs_location"] is True
    r = client.put("/api/profile/location", json={"country": "US", "region": "Texas"})
    assert r.status_code == 200 and r.json()["needs_location"] is False
    assert client.put("/api/profile/location", json={"country": "US", "region": "Goa"}).status_code == 422
    # Settings: change it later, e.g. clear the region.
    assert client.put("/api/profile/location", json={"country": "IN", "region": ""}).json()["region"] is None
    with SessionLocal() as db:
        assert db.scalar(select(User.country).where(User.email == "me@example.com")) == "IN"


def test_admins_arent_asked(client, admin_emails):
    login_admin(client)
    assert client.get("/api/auth/me").json()["needs_location"] is False


def test_export_includes_where_you_live(client, user):
    account = client.get("/api/profile/export").json()["account"]
    assert account["country"] == "IN" and account["region"] == "Maharashtra"
