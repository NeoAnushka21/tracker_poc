"""Alembic environment: the app's own engine (DATABASE_URL) and models.

Run from `backend/`:  .venv\\Scripts\\alembic revision --autogenerate -m "what changed"
The app applies migrations itself at startup (app/migrate.py), passing its connection in
`config.attributes["connection"]`; the command line uses app.db.engine.
"""
from logging.config import fileConfig

from alembic import context

from app import models  # noqa: F401  (registers every table on Base.metadata)
from app.db import Base, engine

config = context.config
target_metadata = Base.metadata


def _configure(connection) -> None:
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        compare_type=True,
        # SQLite can't ALTER most things in place; batch mode rebuilds the table instead.
        render_as_batch=connection.dialect.name == "sqlite",
    )


def run_migrations_offline() -> None:
    context.configure(url=str(engine.url), target_metadata=target_metadata, literal_binds=True,
                      dialect_opts={"paramstyle": "named"})
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connection = config.attributes.get("connection")
    if connection is not None:          # called by the app at startup: keep the app's logging as it is
        _configure(connection)
        with context.begin_transaction():
            context.run_migrations()
        return
    if config.config_file_name is not None:
        fileConfig(config.config_file_name)
    with engine.connect() as conn:
        _configure(conn)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
