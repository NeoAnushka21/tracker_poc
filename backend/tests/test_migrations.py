"""Alembic migrations match the models, build an empty database, and adopt a pre-Alembic one."""
from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext
from alembic.script import ScriptDirectory
from sqlalchemy import inspect, text

from app.db import Base, engine
from app.migrate import alembic_config, migrate


def _reset():
    Base.metadata.drop_all(engine)
    with engine.begin() as conn:
        conn.execute(text("DROP TABLE IF EXISTS alembic_version"))


def _head() -> str:
    return ScriptDirectory.from_config(alembic_config()).get_current_head()


def _current() -> str | None:
    with engine.connect() as conn:
        return MigrationContext.configure(conn).get_current_revision()


def test_migrations_build_an_empty_database_exactly_like_the_models():
    _reset()
    migrate(engine)
    assert _current() == _head()
    with engine.connect() as conn:
        diff = compare_metadata(MigrationContext.configure(conn, opts={"compare_type": True}), Base.metadata)
    assert diff == [], ("Models and migrations disagree. Run `alembic revision --autogenerate -m ...` in "
                        f"backend/ and commit the new file. Differences: {diff}")
    migrate(engine)                     # running again changes nothing
    assert _current() == _head()


def test_a_database_from_before_alembic_is_adopted():
    """E.g. production: tables made by create_all, a column added later without its index."""
    _reset()
    Base.metadata.create_all(engine)
    with engine.begin() as conn:
        conn.execute(text("DROP INDEX ix_users_google_sub"))
        conn.execute(text("DROP TABLE password_resets"))     # a table added after the database was made
    migrate(engine)
    assert _current() == _head()
    insp = inspect(engine)
    assert "password_resets" in insp.get_table_names()
    assert "ix_users_google_sub" in {i["name"] for i in insp.get_indexes("users")}


def test_app_starts_on_a_migrated_database(client):
    assert _current() == _head()
    assert client.get("/api/health").status_code == 200
