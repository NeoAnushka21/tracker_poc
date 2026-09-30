"""Deployment pieces: database URLs, serving the built frontend, and the SQLite -> Postgres copy."""
import os
import sqlite3
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.db import normalize_url
from app.main import mount_frontend


def test_normalize_url_uses_psycopg_for_postgres():
    assert normalize_url("postgres://u:p@h/db?sslmode=require") == "postgresql+psycopg://u:p@h/db?sslmode=require"
    assert normalize_url("postgresql://u:p@h/db") == "postgresql+psycopg://u:p@h/db"
    assert normalize_url("sqlite:///x.db") == "sqlite:///x.db"


@pytest.fixture
def site(tmp_path: Path):
    dist = tmp_path / "dist"
    (dist / "assets").mkdir(parents=True)
    (dist / "index.html").write_text("<html>app</html>")
    (dist / "assets" / "app-123.js").write_text("console.log(1)")
    (dist / "favicon.svg").write_text("<svg/>")
    (dist / "welcome.html").write_text("<html>welcome</html>")
    (tmp_path / "secret.txt").write_text("nope")
    app = FastAPI()

    @app.get("/api/ping")
    def ping():
        return {"ok": True}

    assert mount_frontend(app, dist)
    return TestClient(app)


def test_frontend_served_with_spa_fallback(site):
    assert site.get("/").text == "<html>app</html>"
    assert site.get("/dashboard/anything").text == "<html>app</html>"       # client-side route
    assert site.get("/assets/app-123.js").text == "console.log(1)"
    assert site.get("/favicon.svg").text == "<svg/>"
    assert site.get("/api/ping").json() == {"ok": True}                     # API routes win
    assert site.get("/api/missing").status_code == 404                      # unknown API isn't the app
    assert "nope" not in site.get("/..%2Fsecret.txt").text                  # no escaping dist/


def test_welcome_page_is_served_at_welcome(site):
    """Signed-out visitors land on /welcome (the app redirects there); / is still the app."""
    for path in ("/welcome", "/welcome/", "/welcome.html"):
        r = site.get(path)
        assert r.text == "<html>welcome</html>", path
    assert site.get("/welcome").headers["cache-control"] == "no-cache"
    assert site.get("/").text == "<html>app</html>"


def test_no_frontend_build_means_api_only(tmp_path):
    assert mount_frontend(FastAPI(), tmp_path / "missing") is False


_PG = os.getenv("TEST_DATABASE_URL", "")


@pytest.mark.skipif(not _PG.startswith("postgres"), reason="needs TEST_DATABASE_URL pointing at a throwaway Postgres")
def test_copy_sqlite_to_postgres(client, tmp_path):
    """Build a small SQLite database through the app's models, copy it, check ids and counts."""
    from sqlalchemy import select

    from app.db import Base, make_engine
    from app.models import User, WaterLog
    from scripts.copy_to_postgres import copy_database
    from sqlalchemy.orm import Session

    src_url = f"sqlite:///{tmp_path / 'src.db'}"
    src = make_engine(src_url)
    Base.metadata.create_all(src)
    with Session(src) as db:
        u = User(email="copy@example.com", hashed_password="x")
        db.add(u)
        db.flush()
        db.add_all([WaterLog(user_id=u.id, amount_ml=250, drank_at=u.created_at) for _ in range(3)])
        db.commit()
    # An older source database: a column the models have but SQLite doesn't is copied as empty.
    with sqlite3.connect(tmp_path / "src.db") as con:
        con.execute("ALTER TABLE users DROP COLUMN guide_seen_at")

    with pytest.raises(SystemExit):              # the client fixture's tables hold nothing, but...
        copy_database(src_url, "sqlite:///elsewhere.db")   # ...the target must be Postgres
    copied = copy_database(src_url, _PG, replace=True, out=lambda *_: None)
    assert copied["users"] == 1 and copied["water_logs"] == 3
    with pytest.raises(SystemExit):              # not empty any more
        copy_database(src_url, _PG, out=lambda *_: None)

    tgt = make_engine(_PG)
    with Session(tgt) as db:
        assert db.scalars(select(User)).one().guide_seen_at is None
        new = WaterLog(user_id=1, amount_ml=100, drank_at=db.scalars(select(User)).one().created_at)
        db.add(new)
        db.commit()
        assert new.id == 4                        # sequence moved past the copied ids


def test_health_is_readable_by_the_launcher(client):
    r = client.get("/api/health", headers={"Origin": "https://omniai-app.onrender.com"})
    assert r.json() == {"ok": True}
    assert r.headers["access-control-allow-origin"] == "*"
    assert r.headers["cache-control"] == "no-store"


def test_health_answers_uptime_monitors(client):
    """UptimeRobot's free plan pings with HEAD; a 405 would show the site as down."""
    r = client.head("/api/health")
    assert r.status_code == 200 and r.content == b""


# --- browser security headers and API docs ---------------------------------------------

def test_security_headers_on_every_response(client):
    for path in ("/api/health", "/api/auth/me"):
        h = client.get(path).headers
        csp = h["content-security-policy"]
        assert "frame-ancestors 'none'" in csp and "object-src 'none'" in csp
        assert "script-src 'self' https://accounts.google.com/gsi/client" in csp   # Google's button allowed
        assert "'unsafe-inline'" not in csp.split("script-src")[1].split(";")[0]   # no inline scripts
        assert h["x-content-type-options"] == "nosniff" and h["x-frame-options"] == "DENY"
        assert "microphone=(self)" in h["permissions-policy"]
        assert "strict-transport-security" not in h           # plain HTTP in tests: no HSTS


def test_hsts_only_over_https(client, monkeypatch):
    from app import config
    monkeypatch.setattr(config, "COOKIE_SECURE", True)
    assert client.get("/api/health").headers["strict-transport-security"] == "max-age=31536000"


def test_api_docs_off_in_production(monkeypatch):
    """Development serves /docs; with COOKIE_SECURE (HTTPS, production) the default is off."""
    import importlib
    from app import config, main
    assert main.app.docs_url == "/docs"                       # tests run as development
    monkeypatch.setenv("COOKIE_SECURE", "true")
    monkeypatch.delenv("API_DOCS", raising=False)
    try:
        assert importlib.reload(config).API_DOCS is False
        monkeypatch.setenv("API_DOCS", "true")
        assert importlib.reload(config).API_DOCS is True      # can be switched back on
    finally:
        monkeypatch.undo()
        importlib.reload(config)


# --- request ids and unexpected errors ------------------------------------------------------

def test_every_response_has_a_request_id(client):
    rid = client.get("/api/health").headers["x-request-id"]
    assert len(rid) == 8 and rid != client.get("/api/health").headers["x-request-id"]


def test_unexpected_error_gives_a_reference_and_is_logged(client, caplog):
    from app.main import app

    def boom():
        raise RuntimeError("secret internals")

    app.add_api_route("/api/test-boom", boom, methods=["POST"])
    try:
        with caplog.at_level("ERROR", logger="omniai"):
            r = client.post("/api/test-boom")
    finally:
        app.router.routes = [rt for rt in app.router.routes if getattr(rt, "path", "") != "/api/test-boom"]
    rid = r.headers["x-request-id"]
    assert r.status_code == 500
    assert r.json() == {"detail": f"Something went wrong on our side (ref {rid}). Please try again."}
    assert "secret internals" not in r.text                        # details stay in the log
    assert "content-security-policy" in r.headers                  # still gets the security headers
    assert any("Unhandled error on POST /api/test-boom" in rec.getMessage() for rec in caplog.records)


def test_sentry_is_off_without_a_dsn_and_private_with_one(monkeypatch):
    import sentry_sdk
    from app import config, observability
    monkeypatch.setattr(config, "SENTRY_DSN", "")
    assert observability.setup_sentry() is False
    seen = {}
    monkeypatch.setattr(sentry_sdk, "init", lambda **kw: seen.update(kw))
    monkeypatch.setattr(config, "SENTRY_DSN", "https://key@o0.ingest.sentry.io/0")
    assert observability.setup_sentry() is True
    assert seen["send_default_pii"] is False and seen["max_request_body_size"] == "never"
    assert seen["include_local_variables"] is False and seen["traces_sample_rate"] == 0
