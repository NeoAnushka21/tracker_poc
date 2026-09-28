"""Copy every table from the local SQLite database into a Postgres database (e.g. Neon).

Usage (from backend/):
    .venv\\Scripts\\python scripts\\copy_to_postgres.py            # copy into an empty target
    .venv\\Scripts\\python scripts\\copy_to_postgres.py --replace  # wipe the target first

The target comes from TARGET_DATABASE_URL (environment or backend/.env); the source from
SOURCE_DATABASE_URL, defaulting to backend/macro_tracker.db. The URLs are never printed.

- Creates the app's tables in the target, then copies rows in foreign-key order inside one
  transaction: either everything is copied or nothing is.
- Refuses to run if the target already holds data, unless --replace is given. --replace drops
  and recreates the target's tables: only use it before the deployed app has real data.
- Keeps row ids, then moves each Postgres id sequence past the highest id, so new rows
  don't collide with copied ones.
- Checks row counts per table afterwards.
Stop the local app first so nothing is written to SQLite mid-copy.
"""
import argparse
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import func, inspect, literal, select, text  # noqa: E402
from sqlalchemy.engine import make_url  # noqa: E402

from app import config, models  # noqa: E402,F401  (models registers the tables)
from app.db import Base, make_engine, normalize_url  # noqa: E402


def copy_database(source_url: str, target_url: str, replace: bool = False, out=print) -> dict[str, int]:
    """Returns {table: rows copied}. Raises if the target isn't Postgres, isn't empty (without
    replace), or the counts don't match afterwards."""
    if not normalize_url(target_url).startswith("postgresql"):
        raise SystemExit("TARGET_DATABASE_URL must be a Postgres URL (postgresql://...).")
    src, tgt = make_engine(source_url), make_engine(target_url)
    tables = Base.metadata.sorted_tables

    if replace:
        Base.metadata.drop_all(tgt)
    Base.metadata.create_all(tgt)
    with tgt.connect() as conn:
        busy = {t.name: n for t in tables if (n := conn.execute(select(func.count()).select_from(t)).scalar())}
    if busy:
        raise SystemExit(f"The target already has data ({busy}). Use --replace to overwrite it "
                         "(only before the deployed app is in use).")

    src_tables = set(inspect(src).get_table_names())
    copied: dict[str, int] = {}
    with src.connect() as s, tgt.begin() as t:
        for table in tables:
            if table.name not in src_tables:
                copied[table.name] = 0
                continue
            have = {c["name"] for c in inspect(src).get_columns(table.name)}
            # Columns newer than the source database are copied as empty (all such columns are nullable).
            cols = [c if c.name in have else literal(None).label(c.name) for c in table.columns]
            rows = [dict(r) for r in s.execute(select(*cols).select_from(table)).mappings()]
            if rows:
                t.execute(table.insert(), rows)
            copied[table.name] = len(rows)
            if "id" in table.c and rows:
                t.execute(text(
                    f"SELECT setval(pg_get_serial_sequence('\"{table.name}\"', 'id'), "
                    f"(SELECT MAX(id) FROM \"{table.name}\"))"))
            out(f"  {table.name:<20} {len(rows):>6} rows")

    with tgt.connect() as conn:
        for table in tables:
            n = conn.execute(select(func.count()).select_from(table)).scalar()
            if n != copied[table.name]:
                raise SystemExit(f"Count mismatch in {table.name}: copied {copied[table.name]}, target has {n}.")
    return copied


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--replace", action="store_true", help="drop and recreate the target's tables first")
    args = parser.parse_args()

    source = os.getenv("SOURCE_DATABASE_URL", f"sqlite:///{config.BACKEND_DIR / 'macro_tracker.db'}")
    target = os.getenv("TARGET_DATABASE_URL", "")
    if not target:
        raise SystemExit("Set TARGET_DATABASE_URL (in backend/.env or the environment) to the Neon connection string.")
    print(f"Copying {make_url(normalize_url(source)).database} -> Postgres at {make_url(normalize_url(target)).host}")
    copied = copy_database(source, target, replace=args.replace)
    print(f"Done: {sum(copied.values())} rows in {len(copied)} tables, counts verified.")


if __name__ == "__main__":
    main()
