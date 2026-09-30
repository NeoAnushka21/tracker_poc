"""database hardening, phase 1

- users.public_id: a UUID for the API and admin screens (existing users get one).
- log_entry_items: user_food_id (linked by name for existing rows), general_id, source.
- Every foreign key recreated with a predictable name and an ON DELETE rule, so deleting a
  user removes their rows in the database itself.
- Timestamps become timestamptz on Postgres (values are UTC already).
- Composite (user_id, date/status) indexes replace the single user_id ones.

Written by hand (autogenerate can't backfill or convert types with USING). SQLite rebuilds a
table for most changes; app/migrate.py switches its foreign-key checks off for the run.

Revision ID: 0003
Revises: 0002
Create Date: 2026-09-30
"""
import re
import uuid
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0003"
down_revision: Union[str, Sequence[str], None] = "0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

NAMING = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}

# (table, column, referred table, ON DELETE)
FOREIGN_KEYS = [
    ("admin_audit", "admin_user_id", "users", None),
    ("admin_audit", "target_user_id", "users", "SET NULL"),
    ("ai_requests", "user_id", "users", "CASCADE"),
    ("body_measurements", "user_id", "users", "CASCADE"),
    ("llm_usage", "user_id", "users", "SET NULL"),
    ("log_entries", "user_id", "users", "CASCADE"),
    ("password_resets", "user_id", "users", "CASCADE"),
    ("user_foods", "user_id", "users", "CASCADE"),
    ("user_targets", "user_id", "users", "CASCADE"),
    ("water_logs", "user_id", "users", "CASCADE"),
    ("weight_logs", "user_id", "users", "CASCADE"),
    ("chat_messages", "related_log_entry_id", "log_entries", "SET NULL"),
    ("chat_messages", "user_id", "users", "CASCADE"),
    ("log_entry_items", "log_entry_id", "log_entries", "CASCADE"),
    ("recipe_ingredients", "recipe_id", "user_foods", "CASCADE"),
    ("recipe_ingredients", "food_id", "user_foods", "CASCADE"),   # the app refuses to delete a used ingredient
    ("pending_actions", "target_entry_id", "log_entries", "SET NULL"),
    ("pending_actions", "chat_message_id", "chat_messages", "SET NULL"),
    ("pending_actions", "result_entry_id", "log_entries", "SET NULL"),
    ("pending_actions", "user_id", "users", "CASCADE"),
]

TIMESTAMPS = {
    "users": ["totp_enabled_at", "created_at", "consent_at", "last_login_at", "guide_seen_at"],
    "admin_audit": ["created_at"], "ai_requests": ["created_at"], "body_measurements": ["measured_at"],
    "llm_usage": ["created_at"], "log_entries": ["eaten_at", "created_at", "updated_at", "deleted_at"],
    "password_resets": ["created_at", "expires_at", "used_at"],
    "user_foods": ["created_at", "updated_at", "last_used_at"], "user_targets": ["created_at"],
    "water_logs": ["drank_at", "created_at"], "weight_logs": ["logged_at"], "chat_messages": ["created_at"],
    "pending_actions": ["created_at", "resolved_at"],
}

# table -> second column of the new (user_id, ...) index, which replaces ix_<table>_user_id
COMPOSITE = {
    "weight_logs": "logged_at", "user_targets": "effective_date", "log_entries": "eaten_at",
    "body_measurements": "measured_at", "water_logs": "drank_at", "user_foods": "last_used_at",
    "pending_actions": "status", "chat_messages": "created_at", "ai_requests": "created_at",
}


def _new_id() -> uuid.UUID:
    return uuid.uuid7() if hasattr(uuid, "uuid7") else uuid.uuid4()


def _name_key(name: str, brand: str | None) -> str:
    """Same as services/foods.name_key at the time of writing (copied so this file never changes)."""
    return " ".join(re.sub(r"[^a-z0-9]+", " ", f"{name} {brand or ''}".lower()).split())


def upgrade() -> None:
    bind = op.get_bind()
    sqlite = bind.dialect.name == "sqlite"

    # 1. users.public_id ------------------------------------------------------------------
    with op.batch_alter_table("users") as b:
        b.add_column(sa.Column("public_id", sa.Uuid(), nullable=True))
    users = sa.table("users", sa.column("id", sa.Integer), sa.column("public_id", sa.Uuid))
    for (uid,) in bind.execute(sa.select(users.c.id)).all():
        bind.execute(users.update().where(users.c.id == uid).values(public_id=_new_id()))
    with op.batch_alter_table("users") as b:
        b.alter_column("public_id", existing_type=sa.Uuid(), nullable=False)
        b.create_unique_constraint("uq_users_public_id", ["public_id"])

    # 2. log_entry_items: where the numbers came from --------------------------------------
    with op.batch_alter_table("log_entry_items") as b:
        b.add_column(sa.Column("user_food_id", sa.Integer(), nullable=True))
        b.add_column(sa.Column("general_id", sa.String(80), nullable=True))
        b.add_column(sa.Column("source", sa.String(10), nullable=True))
        b.create_index("ix_log_entry_items_user_food_id", ["user_food_id"])
        b.create_foreign_key("fk_log_entry_items_user_food_id_user_foods", "user_foods",
                             ["user_food_id"], ["id"], ondelete="SET NULL")
    foods = bind.execute(sa.text("SELECT id, user_id, name, brand_name FROM user_foods")).all()
    by_key = {(f.user_id, _name_key(f.name, f.brand_name)): f.id for f in foods}
    items = bind.execute(sa.text(
        "SELECT i.id, e.user_id, i.ingredient_name, i.brand_name FROM log_entry_items i "
        "JOIN log_entries e ON e.id = i.log_entry_id")).all()
    for it in items:
        food_id = by_key.get((it.user_id, _name_key(it.ingredient_name, it.brand_name)))
        if food_id is not None:
            bind.execute(sa.text("UPDATE log_entry_items SET user_food_id = :f WHERE id = :i"),
                         {"f": food_id, "i": it.id})

    # 3. foreign keys: predictable names + ON DELETE rules -----------------------------------
    by_table: dict[str, list[tuple]] = {}
    for table, col, ref, ondelete in FOREIGN_KEYS:
        by_table.setdefault(table, []).append((col, ref, ondelete))
    for table, fks in by_table.items():
        if sqlite:
            # Reflected SQLite FKs have no name; the convention names them so they can be dropped.
            with op.batch_alter_table(table, recreate="always", naming_convention=NAMING) as b:
                for col, ref, ondelete in fks:
                    name = f"fk_{table}_{col}_{ref}"
                    b.drop_constraint(name, type_="foreignkey")
                    b.create_foreign_key(name, ref, [col], ["id"], ondelete=ondelete)
        else:
            existing = sa.inspect(bind).get_foreign_keys(table)
            for col, ref, ondelete in fks:
                for fk in existing:
                    if fk["constrained_columns"] == [col] and fk["name"]:
                        op.drop_constraint(fk["name"], table, type_="foreignkey")
                op.create_foreign_key(f"fk_{table}_{col}_{ref}", table, ref, [col], ["id"], ondelete=ondelete)

    # 4. timestamptz (Postgres only; SQLite has no such type) -----------------------------------
    if not sqlite:
        for table, cols in TIMESTAMPS.items():
            for col in cols:
                op.alter_column(table, col, type_=sa.DateTime(timezone=True), existing_type=sa.DateTime(),
                                postgresql_using=f"{col} AT TIME ZONE 'UTC'")

    # 5. composite indexes ----------------------------------------------------------------------
    for table, second in COMPOSITE.items():
        op.create_index(f"ix_{table}_user_id_{second}", table, ["user_id", second])
        op.drop_index(f"ix_{table}_user_id", table_name=table)
    op.drop_index("ix_user_foods_last_used_at", table_name="user_foods")


def downgrade() -> None:
    bind = op.get_bind()
    sqlite = bind.dialect.name == "sqlite"
    op.create_index("ix_user_foods_last_used_at", "user_foods", ["last_used_at"])
    for table, second in COMPOSITE.items():
        op.create_index(f"ix_{table}_user_id", table, ["user_id"])
        op.drop_index(f"ix_{table}_user_id_{second}", table_name=table)
    if not sqlite:
        for table, cols in TIMESTAMPS.items():
            for col in cols:
                op.alter_column(table, col, type_=sa.DateTime(), existing_type=sa.DateTime(timezone=True),
                                postgresql_using=f"{col} AT TIME ZONE 'UTC'")
    # Foreign keys keep their new names and delete rules (harmless for the older code).
    with op.batch_alter_table("log_entry_items", naming_convention=NAMING) as b:
        b.drop_constraint("fk_log_entry_items_user_food_id_user_foods", type_="foreignkey")
        b.drop_index("ix_log_entry_items_user_food_id")
        b.drop_column("source")
        b.drop_column("general_id")
        b.drop_column("user_food_id")
    with op.batch_alter_table("users") as b:
        b.drop_constraint("uq_users_public_id", type_="unique")
        b.drop_column("public_id")
