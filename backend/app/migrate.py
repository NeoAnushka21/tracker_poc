r"""Database schema at startup: Alembic migrations (backend/migrations).

- Empty database: every migration runs (the baseline creates all tables).
- Database from before Alembic (2026-09-29, e.g. Neon): it's brought up to the current models the old
  way (missing tables, nullable columns and indexes) and marked as the latest revision. (Marking it as
  the baseline would make later migrations re-add columns it already has.)
- Otherwise: pending migrations run.

To change the schema: edit app/models.py, then from backend/ run
    .venv\Scripts\alembic revision --autogenerate -m "what changed"
review the generated file in migrations/versions/, and commit it. tests/test_migrations.py fails if
the models and the migrations disagree.
"""
import logging
from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import inspect
from sqlalchemy.engine import Engine

from app import models  # noqa: F401  (registers every table)
from app.db import Base, add_missing_columns

log = logging.getLogger("omniai.migrate")
BACKEND = Path(__file__).resolve().parent.parent


def alembic_config() -> Config:
    cfg = Config(str(BACKEND / "alembic.ini"))
    cfg.set_main_option("script_location", str(BACKEND / "migrations"))
    return cfg


def migrate(engine: Engine) -> None:
    cfg = alembic_config()
    with engine.begin() as conn:
        cfg.attributes["connection"] = conn
        tables = set(inspect(conn).get_table_names())
        if "alembic_version" not in tables and "users" in tables:
            log.info("Database from before migrations: bringing it up to date and marking it as current")
            Base.metadata.create_all(conn)            # tables added since it was made
            added = add_missing_columns(conn)
            for table in Base.metadata.sorted_tables:  # indexes the old column adder didn't create
                for index in table.indexes:
                    index.create(conn, checkfirst=True)
            if added:
                log.info("Added columns: %s", ", ".join(added))
            command.stamp(cfg, "head")
        command.upgrade(cfg, "head")
