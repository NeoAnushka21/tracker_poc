"""Database schema.

All datetimes are stored as naive UTC. Conversion to the user's local time
happens at the edges (see timeutil.py).

Differences from the spec's starting schema:
- Proposed writes (create/edit/delete) live in `pending_actions` rather than
  as `status=pending` rows in `log_entries`. That gives edits and deletes of
  confirmed entries somewhere to wait for confirmation too, and means
  `log_entries` only ever holds confirmed data.
- `log_entries.eaten_at` (when the food was eaten) is separate from
  `created_at` (when it was logged), so "yesterday's lunch" works.
- Deletes are soft (`deleted_at`).
"""
from datetime import date, datetime, timezone

from sqlalchemy import JSON, Date, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255))
    preferred_name: Mapped[str | None] = mapped_column(String(80))
    date_of_birth: Mapped[date | None] = mapped_column(Date)
    sex: Mapped[str | None] = mapped_column(String(10))            # male | female
    height_cm: Mapped[float | None] = mapped_column(Float)
    unit_system: Mapped[str] = mapped_column(String(10), default="metric")
    timezone: Mapped[str] = mapped_column(String(64), default="UTC")
    goal_type: Mapped[str | None] = mapped_column(String(32))
    activity_level: Mapped[str | None] = mapped_column(String(32))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    consent_at: Mapped[datetime | None] = mapped_column(DateTime)
    consent_version: Mapped[str | None] = mapped_column(String(32))
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime)
    login_count: Mapped[int | None] = mapped_column(Integer, default=0)
    guide_seen_at: Mapped[datetime | None] = mapped_column(DateTime)   # first-run tour finished or skipped

    @property
    def onboarded(self) -> bool:
        return self.date_of_birth is not None and self.goal_type is not None


class WeightLog(Base):
    __tablename__ = "weight_logs"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    weight_kg: Mapped[float] = mapped_column(Float)
    logged_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class UserTarget(Base):
    __tablename__ = "user_targets"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    daily_calorie_target: Mapped[int] = mapped_column(Integer)
    protein_target_g: Mapped[int] = mapped_column(Integer)
    carbs_target_g: Mapped[int] = mapped_column(Integer)
    fat_target_g: Mapped[int] = mapped_column(Integer)
    effective_date: Mapped[date] = mapped_column(Date)
    is_custom: Mapped[bool] = mapped_column(default=False)   # user edited vs calculated
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class LogEntry(Base):
    __tablename__ = "log_entries"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    eaten_at: Mapped[datetime] = mapped_column(DateTime, index=True)
    meal_type: Mapped[str] = mapped_column(String(16))
    raw_user_message: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime)

    items: Mapped[list["LogEntryItem"]] = relationship(
        back_populates="entry", cascade="all, delete-orphan", order_by="LogEntryItem.id"
    )


class LogEntryItem(Base):
    __tablename__ = "log_entry_items"

    id: Mapped[int] = mapped_column(primary_key=True)
    log_entry_id: Mapped[int] = mapped_column(ForeignKey("log_entries.id"), index=True)
    ingredient_name: Mapped[str] = mapped_column(String(200))
    brand_name: Mapped[str | None] = mapped_column(String(200))
    quantity: Mapped[float] = mapped_column(Float)
    unit: Mapped[str] = mapped_column(String(32))
    calories: Mapped[float] = mapped_column(Float)
    protein_g: Mapped[float] = mapped_column(Float)
    carbs_g: Mapped[float] = mapped_column(Float)
    fat_g: Mapped[float] = mapped_column(Float)
    fiber_g: Mapped[float] = mapped_column(Float, default=0)
    micronutrients: Mapped[dict | None] = mapped_column(JSON)   # {iron_mg: 1.2, ...}; keys in config

    entry: Mapped[LogEntry] = relationship(back_populates="items")


class AdminAudit(Base):
    """Every time an admin opens a user's data."""
    __tablename__ = "admin_audit"

    id: Mapped[int] = mapped_column(primary_key=True)
    admin_user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    target_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), index=True)
    action: Mapped[str] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class BodyMeasurement(Base):
    """One dated set of optional body measurements (cm). Any subset may be filled."""
    __tablename__ = "body_measurements"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    measured_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, index=True)
    neck_cm: Mapped[float | None] = mapped_column(Float)
    chest_cm: Mapped[float | None] = mapped_column(Float)
    waist_cm: Mapped[float | None] = mapped_column(Float)
    hips_cm: Mapped[float | None] = mapped_column(Float)
    biceps_cm: Mapped[float | None] = mapped_column(Float)
    forearm_cm: Mapped[float | None] = mapped_column(Float)
    thigh_cm: Mapped[float | None] = mapped_column(Float)
    calf_cm: Mapped[float | None] = mapped_column(Float)


class WaterLog(Base):
    """Plain drinking water, tracked separately from food."""
    __tablename__ = "water_logs"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    amount_ml: Mapped[float] = mapped_column(Float)
    drank_at: Mapped[datetime] = mapped_column(DateTime, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class UserFood(Base):
    """A food in the user's personal library, or a saved recipe.

    Nutrients are stored for a reference amount (`ref_qty` `ref_unit`), e.g. 100 g,
    100 ml, 1 piece or 1 serving. Optional gram weights for a piece/serving let one
    record answer "3 almonds" and "30 g almonds" alike. Scaling is done in code
    (services/foods.py), so the LLM never does the arithmetic for known foods.
    """
    __tablename__ = "user_foods"
    __table_args__ = (UniqueConstraint("user_id", "name_key", name="uq_user_food_name"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    name: Mapped[str] = mapped_column(String(200))
    name_key: Mapped[str] = mapped_column(String(260))           # normalised name + brand
    brand_name: Mapped[str | None] = mapped_column(String(200))
    kind: Mapped[str] = mapped_column(String(10), default="food")  # food | recipe
    # estimate (from the LLM, confirmed by the user) | user (edited by hand) | recipe
    source: Mapped[str] = mapped_column(String(10), default="estimate")

    ref_qty: Mapped[float] = mapped_column(Float)
    ref_unit: Mapped[str] = mapped_column(String(32))              # g | ml | piece | serving | cup...
    calories: Mapped[float] = mapped_column(Float)
    protein_g: Mapped[float] = mapped_column(Float)
    carbs_g: Mapped[float] = mapped_column(Float)
    fat_g: Mapped[float] = mapped_column(Float)
    fiber_g: Mapped[float] = mapped_column(Float, default=0)
    grams_per_piece: Mapped[float | None] = mapped_column(Float)
    grams_per_serving: Mapped[float | None] = mapped_column(Float)
    micronutrients: Mapped[dict | None] = mapped_column(JSON)       # per reference amount

    # Recipe yield (recipes only): at least one is set.
    yield_pieces: Mapped[float | None] = mapped_column(Float)
    yield_servings: Mapped[float | None] = mapped_column(Float)
    cooked_weight_g: Mapped[float | None] = mapped_column(Float)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)
    last_used_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, index=True)

    ingredients: Mapped[list["RecipeIngredient"]] = relationship(
        foreign_keys="RecipeIngredient.recipe_id",
        cascade="all, delete-orphan",
        order_by="RecipeIngredient.id",
    )


class RecipeIngredient(Base):
    __tablename__ = "recipe_ingredients"

    id: Mapped[int] = mapped_column(primary_key=True)
    recipe_id: Mapped[int] = mapped_column(ForeignKey("user_foods.id"), index=True)
    food_id: Mapped[int] = mapped_column(ForeignKey("user_foods.id"), index=True)
    quantity: Mapped[float] = mapped_column(Float)
    unit: Mapped[str] = mapped_column(String(32))

    food: Mapped[UserFood] = relationship(foreign_keys=[food_id])


class PendingAction(Base):
    """A write the LLM has proposed and the user has not yet confirmed."""
    __tablename__ = "pending_actions"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    action_type: Mapped[str] = mapped_column(String(16))           # create | edit | delete | save_recipe
    target_entry_id: Mapped[int | None] = mapped_column(ForeignKey("log_entries.id"))
    payload: Mapped[dict] = mapped_column(JSON)
    # pending | confirmed | rejected | superseded | expired
    status: Mapped[str] = mapped_column(String(16), default="pending", index=True)
    chat_message_id: Mapped[int | None] = mapped_column(ForeignKey("chat_messages.id"))
    result_entry_id: Mapped[int | None] = mapped_column(ForeignKey("log_entries.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime)


class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    # user | assistant | event (event = app-generated note, e.g. "user confirmed #12")
    role: Mapped[str] = mapped_column(String(16))
    content: Mapped[str] = mapped_column(Text)
    kind: Mapped[str | None] = mapped_column(String(16))     # e.g. "progress" (day-so-far card)
    data: Mapped[dict | None] = mapped_column(JSON)          # structured data for that card
    related_log_entry_id: Mapped[int | None] = mapped_column(ForeignKey("log_entries.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, index=True)

    actions: Mapped[list[PendingAction]] = relationship(
        primaryjoin="ChatMessage.id == PendingAction.chat_message_id",
        order_by="PendingAction.id",
        viewonly=True,
    )
