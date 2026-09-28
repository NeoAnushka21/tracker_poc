from sqlalchemy import create_engine, event
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


class Base(DeclarativeBase):
    pass


def add_missing_columns() -> list[str]:
    """Tiny forward-only migration: add columns that exist in the models but not in the
    database (new nullable columns only). Enough for this app until it adopts Alembic."""
    from sqlalchemy import inspect, text

    added = []
    with engine.begin() as conn:
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
                col_type = col.type.compile(dialect=engine.dialect)
                conn.execute(text(f'ALTER TABLE "{table.name}" ADD COLUMN "{col.name}" {col_type}'))
                added.append(f"{table.name}.{col.name}")
    return added


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
