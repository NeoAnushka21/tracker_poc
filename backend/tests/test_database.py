"""Database hardening, phase 1 (migration 0003): public user ids, logged items linked to their
food, delete rules in the database, UTC timestamps, and the upgrade of existing data."""
import uuid
from datetime import datetime

from alembic import command
from sqlalchemy import func, select, text

from app.db import Base, SessionLocal, engine
from app.migrate import alembic_config, migrate
from app.models import LlmUsage, LogEntryItem, User, UserFood, utcnow
from tests.conftest import internal_id
from tests.test_admin import login_admin
from tests.test_admin import admin_emails  # noqa: F401  (fixture)
from tests.test_dashboard_add import add
from tests.test_foods import CHICKEN, log_and_confirm
from tests.test_routing import chat


# --- public ids --------------------------------------------------------------------------------

def test_the_api_shows_a_uuid_not_the_internal_id(client, user, admin_emails):
    public = client.get("/api/auth/me").json()["id"]
    assert uuid.UUID(public).version in (4, 7)
    client.post("/api/auth/logout")
    login_admin(client)
    [row] = [u for u in client.get("/api/admin/users").json() if u["email"] == "me@example.com"]
    assert row["id"] == public
    assert client.get(f"/api/admin/users/{public}").status_code == 200


# --- logged items point at their food ------------------------------------------------------------

def _items() -> list[LogEntryItem]:
    with SessionLocal() as db:
        return list(db.scalars(select(LogEntryItem).order_by(LogEntryItem.id)))


def test_logged_items_are_linked_to_their_saved_food(client, user, fake_llm):
    log_and_confirm(client, fake_llm, [CHICKEN])                        # an AI estimate, learned on confirm
    fake_llm()
    card = chat(client, "had 150 g banana")["actions"][0]               # the general list, learned on confirm
    client.post(f"/api/actions/{card['id']}/confirm")
    add(client, name="banana", quantity=100, unit="g", meal_type="dinner")   # Dashboard: saved food, direct
    with SessionLocal() as db:
        foods = {f.name: f.id for f in db.scalars(select(UserFood))}
    got = [(i.ingredient_name, i.user_food_id, i.source) for i in _items()]
    assert got == [("chicken breast, cooked", foods["chicken breast, cooked"], "estimate"),
                   ("banana", foods["banana"], "general"),
                   ("banana", foods["banana"], "library")]
    # "Most eaten" is now a plain count.
    with SessionLocal() as db:
        most = db.execute(select(LogEntryItem.user_food_id, func.count()).group_by(LogEntryItem.user_food_id)
                          .order_by(func.count().desc())).first()
    assert most == (foods["banana"], 2)


def test_deleting_a_saved_food_keeps_the_log(client, user, fake_llm):
    log_and_confirm(client, fake_llm, [CHICKEN])
    food_id = client.get("/api/foods").json()[0]["id"]
    assert client.delete(f"/api/foods/{food_id}").status_code in (200, 204)
    [item] = _items()
    assert item.user_food_id is None and item.calories == 165           # link cleared, numbers kept


# --- delete rules ---------------------------------------------------------------------------------

def test_account_deletion_leaves_no_row_in_any_table(client, user, fake_llm):
    log_and_confirm(client, fake_llm, [CHICKEN])
    fake_llm()
    chat(client, "200 g rice")                                          # a question with data on the reply
    client.post("/api/water", json={"amount_ml": 250})
    uid = internal_id(user["id"])
    with SessionLocal() as db:
        db.add(LlmUsage(user_id=uid, provider="groq", model="m", tier="small", intent="log", outcome="ok"))
        db.commit()
    assert client.post("/api/auth/delete-account", json={"password": "password123"}).status_code == 200

    kept_unlinked = {"llm_usage", "admin_audit"}
    with engine.connect() as conn:
        for table in Base.metadata.sorted_tables:                      # every table, incl. ones added later
            if "user_id" in table.c:
                n = conn.execute(select(func.count()).select_from(table).where(table.c.user_id == uid)).scalar()
                assert n == 0, table.name
        assert conn.execute(text("SELECT COUNT(*) FROM log_entry_items")).scalar() == 0
        assert conn.execute(text("SELECT COUNT(*) FROM llm_usage WHERE user_id IS NULL")).scalar() >= 1   # kept, unlinked
    assert kept_unlinked <= {t.name for t in Base.metadata.sorted_tables}


# --- timestamps -------------------------------------------------------------------------------------

def test_times_come_back_as_naive_utc(client, user):
    before = utcnow()
    with SessionLocal() as db:
        u = db.scalar(select(User))
        assert u.created_at.tzinfo is None and abs((u.created_at - before).total_seconds()) < 60
        u.last_login_at = datetime(2026, 9, 30, 12, 0)
        db.commit()
    with SessionLocal() as db:
        assert db.scalar(select(User)).last_login_at == datetime(2026, 9, 30, 12, 0)


# --- upgrading existing data (0002 -> 0003) -----------------------------------------------------------

def test_upgrade_gives_existing_users_ids_and_links_old_items():
    Base.metadata.drop_all(engine)
    with engine.begin() as conn:
        conn.execute(text("DROP TABLE IF EXISTS alembic_version"))
    cfg = alembic_config()
    with engine.begin() as conn:
        cfg.attributes["connection"] = conn
        command.upgrade(cfg, "0002")
        conn.execute(text("INSERT INTO users (id, email, hashed_password, unit_system, timezone, created_at) "
                          "VALUES (1, 'a@x.com', 'h', 'metric', 'UTC', '2026-09-01 10:00:00'), "
                          "(2, 'b@x.com', 'h', 'metric', 'UTC', '2026-09-01 10:00:00')"))
        conn.execute(text("INSERT INTO user_foods (id, user_id, name, name_key, kind, source, ref_qty, ref_unit, "
                          "calories, protein_g, carbs_g, fat_g, fiber_g, created_at, updated_at, last_used_at) "
                          "VALUES (5, 1, 'Paneer', 'paneer', 'food', 'estimate', 100, 'g', 265, 18, 1, 21, 0, "
                          "'2026-09-01', '2026-09-01', '2026-09-01')"))
        conn.execute(text("INSERT INTO log_entries (id, user_id, eaten_at, meal_type, created_at, updated_at) "
                          "VALUES (7, 1, '2026-09-02 08:00:00', 'breakfast', '2026-09-02', '2026-09-02')"))
        conn.execute(text("INSERT INTO log_entry_items (log_entry_id, ingredient_name, quantity, unit, calories, "
                          "protein_g, carbs_g, fat_g, fiber_g) VALUES (7, 'paneer', 100, 'g', 265, 18, 1, 21, 0), "
                          "(7, 'mango', 1, 'piece', 200, 1, 50, 1, 5)"))
    migrate(engine)                                                   # the app's own upgrade path
    with SessionLocal() as db:
        ids = [u.public_id for u in db.scalars(select(User))]
        assert len(ids) == 2 and len(set(ids)) == 2 and all(ids)
        items = db.scalars(select(LogEntryItem).order_by(LogEntryItem.id))
        assert [(i.ingredient_name, i.user_food_id) for i in items] == \
            [("paneer", 5), ("mango", None)]                          # linked by name where possible
        assert db.get(User, 1).created_at == datetime(2026, 9, 1, 10, 0)
