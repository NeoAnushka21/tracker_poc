from datetime import timezone

from sqlalchemy import DateTime, MetaData, TypeDecorator, create_engine, event
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.config import DATABASE_URL


def normalize_url(url: str) -> str:
    """Hosts (Neon, Render) hand out postgres:// or postgresql:// URLs; use the psycopg 3 driver."""
    for prefix in ("postgres://", "postgresql://"):
        if url.startswith(prefix):
            return "postgresql+psycopg://" + url[len(prefix):]
    return url


def make_engine(url: str):
    url = normalize_url(url)
    if url.startswith("sqlite"):
        return create_engine(url, connect_args={"check_same_thread": False})
    # Neon suspends idle databases and drops their connections, so check each pooled
    # connection before use and recycle it before the host would close it.
    return create_engine(url, pool_pre_ping=True, pool_recycle=300, pool_size=5, max_overflow=5)


_is_sqlite = normalize_url(DATABASE_URL).startswith("sqlite")
engine = make_engine(DATABASE_URL)

if _is_sqlite:
    @event.listens_for(engine, "connect")
    def _enable_sqlite_fks(dbapi_conn, _):
        dbapi_conn.execute("PRAGMA foreign_keys=ON")


SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


# Predictable names for every index and constraint, so later migrations can find them by name on
# Postgres (2026-09-30). ix_ matches the names SQLAlchemy already gave indexes.
NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    metadata = MetaData(naming_convention=NAMING_CONVENTION)


class UTCDateTime(TypeDecorator):
    """A UTC moment: `timestamptz` in Postgres (unambiguous for any tool reading the database),
    while the app keeps working with naive UTC datetimes as before (models.utcnow)."""
    impl = DateTime(timezone=True)
    cache_ok = True

    def process_bind_param(self, value, dialect):
        if value is not None and value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        return value

    def process_result_value(self, value, dialect):
        if value is not None and value.tzinfo is not None:
            value = value.astimezone(timezone.utc).replace(tzinfo=None)
        return value


def add_missing_columns(connection=None) -> list[str]:
    """Add nullable columns that exist in the models but not in the database. Since Alembic (2026-09-29)
    this only brings a database from before then up to the baseline (app/migrate.py)."""
    from contextlib import nullcontext
    from sqlalchemy import inspect, text

    added = []
    with (nullcontext(connection) if connection is not None else engine.begin()) as conn:
        insp = inspect(conn)   # same connection as the ALTERs, so both see one schema
        existing_tables = set(insp.get_table_names())
        for table in Base.metadata.sorted_tables:
            if table.name not in existing_tables:
                continue
            have = {c["name"] for c in insp.get_columns(table.name)}
            for col in table.columns:
                if col.name in have:
                    continue
                if not col.nullable:
                    raise RuntimeError(f"Can't auto-add NOT NULL column {table.name}.{col.name}")
                col_type = col.type.compile(dialect=conn.dialect)
                conn.execute(text(f'ALTER TABLE "{table.name}" ADD COLUMN "{col.name}" {col_type}'))
                added.append(f"{table.name}.{col.name}")
    return added


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
