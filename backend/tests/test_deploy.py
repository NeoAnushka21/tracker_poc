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
