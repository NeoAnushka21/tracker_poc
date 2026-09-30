"""Database schema.

All datetimes are UTC: `timestamptz` in Postgres, naive UTC datetimes in Python
(db.UTCDateTime). Conversion to the user's local time happens at the edges (see timeutil.py).

Identity: `users.id` is the internal key every table joins on; `users.public_id` (a UUID) is
what the API and the admin screens show, so ids can't be guessed or counted. Deleting a user
removes their rows through ON DELETE CASCADE (usage and audit rows are kept, unlinked).

Differences from the spec's starting schema:
- Proposed writes (create/edit/delete) live in `pending_actions` rather than
  as `status=pending` rows in `log_entries`. That gives edits and deletes of
  confirmed entries somewhere to wait for confirmation too, and means
  `log_entries` only ever holds confirmed data.
- `log_entries.eaten_at` (when the food was eaten) is separate from
  `created_at` (when it was logged), so "yesterday's lunch" works.
- Deletes are soft (`deleted_at`).
"""
import uuid
from datetime import date, datetime, timezone

from sqlalchemy import JSON, Boolean, Date, Float, ForeignKey, Index, Integer, String, Text, UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base, UTCDateTime


def utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def new_public_id() -> uuid.UUID:
    """Time-ordered UUID v7 (index-friendly), where Python has it; else a random v4."""
    return uuid.uuid7() if hasattr(uuid, "uuid7") else uuid.uuid4()


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    public_id: Mapped[uuid.UUID] = mapped_column(Uuid, unique=True, default=new_public_id)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    # "" for accounts created with Google and no password set (the column is NOT NULL).
    hashed_password: Mapped[str] = mapped_column(String(255))
    google_sub: Mapped[str | None] = mapped_column(String(255), index=True)   # Google account id, when linked
    # Put in every session token; bumping it ends all sessions (password change, log out everywhere).
    # None = 0 (accounts from before this column).
    session_version: Mapped[int | None] = mapped_column(Integer, default=0)
    # Two-step sign-in (admin): encrypted TOTP secret, when it was switched on, last accepted time step.
    totp_secret: Mapped[str | None] = mapped_column(String(255))
    totp_enabled_at: Mapped[datetime | None] = mapped_column(UTCDateTime)
    totp_last_step: Mapped[int | None] = mapped_column(Integer)
    preferred_name: Mapped[str | None] = mapped_column(String(80))
    date_of_birth: Mapped[date | None] = mapped_column(Date)
    sex: Mapped[str | None] = mapped_column(String(10))            # male | female
    height_cm: Mapped[float | None] = mapped_column(Float)
    unit_system: Mapped[str] = mapped_column(String(10), default="metric")
    timezone: Mapped[str] = mapped_column(String(64), default="UTC")
    goal_type: Mapped[str | None] = mapped_column(String(32))
    activity_level: Mapped[str | None] = mapped_column(String(32))
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow)
    consent_at: Mapped[datetime | None] = mapped_column(UTCDateTime)
    consent_version: Mapped[str | None] = mapped_column(String(32))
    last_login_at: Mapped[datetime | None] = mapped_column(UTCDateTime)
    login_count: Mapped[int | None] = mapped_column(Integer, default=0)
    guide_seen_at: Mapped[datetime | None] = mapped_column(UTCDateTime)   # first-run tour finished or skipped

    @property
    def onboarded(self) -> bool:
        return self.date_of_birth is not None and self.goal_type is not None


class WeightLog(Base):
    __tablename__ = "weight_logs"
    __table_args__ = (Index("ix_weight_logs_user_id_logged_at", "user_id", "logged_at"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    weight_kg: Mapped[float] = mapped_column(Float)
    logged_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow)


class UserTarget(Base):
    __tablename__ = "user_targets"
    __table_args__ = (Index("ix_user_targets_user_id_effective_date", "user_id", "effective_date"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    daily_calorie_target: Mapped[int] = mapped_column(Integer)
    protein_target_g: Mapped[int] = mapped_column(Integer)
    carbs_target_g: Mapped[int] = mapped_column(Integer)
    fat_target_g: Mapped[int] = mapped_column(Integer)
    effective_date: Mapped[date] = mapped_column(Date)
    is_custom: Mapped[bool] = mapped_column(default=False)   # user edited vs calculated
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow)


class LogEntry(Base):
    __tablename__ = "log_entries"
    __table_args__ = (Index("ix_log_entries_user_id_eaten_at", "user_id", "eaten_at"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    eaten_at: Mapped[datetime] = mapped_column(UTCDateTime, index=True)
    meal_type: Mapped[str] = mapped_column(String(16))
    raw_user_message: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow, onupdate=utcnow)
    deleted_at: Mapped[datetime | None] = mapped_column(UTCDateTime)

    items: Mapped[list["LogEntryItem"]] = relationship(
        back_populates="entry", cascade="all, delete-orphan", order_by="LogEntryItem.id"
    )


class LogEntryItem(Base):
    __tablename__ = "log_entry_items"

    id: Mapped[int] = mapped_column(primary_key=True)
    log_entry_id: Mapped[int] = mapped_column(ForeignKey("log_entries.id", ondelete="CASCADE"), index=True)
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
    # Where the numbers came from (2026-09-30): the saved food it was logged from or learned into
    # (so "most eaten" is a count, not name matching), the general-list id, and the source
    # (library | general | estimate | recipe). Older rows were linked by name where possible.
    user_food_id: Mapped[int | None] = mapped_column(ForeignKey("user_foods.id", ondelete="SET NULL"), index=True)
    general_id: Mapped[str | None] = mapped_column(String(80))
    source: Mapped[str | None] = mapped_column(String(10))

    entry: Mapped[LogEntry] = relationship(back_populates="items")


class LlmUsage(Base):
    """One row per model call (or rule-based fast-path reply), for quota tracking and the admin view."""
    __tablename__ = "llm_usage"

    id: Mapped[int] = mapped_column(primary_key=True)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow, index=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), index=True)
    provider: Mapped[str] = mapped_column(String(40))        # e.g. groq, fastpath
    model: Mapped[str] = mapped_column(String(120))
    tier: Mapped[str] = mapped_column(String(10))            # small | large | none
    intent: Mapped[str] = mapped_column(String(20))
    prompt_tokens: Mapped[int | None] = mapped_column(Integer)
    completion_tokens: Mapped[int | None] = mapped_column(Integer)
    latency_ms: Mapped[int | None] = mapped_column(Integer)
    outcome: Mapped[str] = mapped_column(String(20))         # ok | error | rate_limited | fastpath
    escalated: Mapped[bool | None] = mapped_column(Boolean, default=False)


class AdminAudit(Base):
    """Every time an admin opens a user's data."""
    __tablename__ = "admin_audit"

    id: Mapped[int] = mapped_column(primary_key=True)
    admin_user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    target_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), index=True)
    action: Mapped[str] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow)


class BodyMeasurement(Base):
    """One dated set of optional body measurements (cm). Any subset may be filled."""
    __tablename__ = "body_measurements"
    __table_args__ = (Index("ix_body_measurements_user_id_measured_at", "user_id", "measured_at"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    measured_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow, index=True)
    neck_cm: Mapped[float | None] = mapped_column(Float)
    shoulders_cm: Mapped[float | None] = mapped_column(Float)
    chest_cm: Mapped[float | None] = mapped_column(Float)
    waist_cm: Mapped[float | None] = mapped_column(Float)
    hips_cm: Mapped[float | None] = mapped_column(Float)
    biceps_cm: Mapped[float | None] = mapped_column(Float)
    forearm_cm: Mapped[float | None] = mapped_column(Float)
    wrist_cm: Mapped[float | None] = mapped_column(Float)
    thigh_cm: Mapped[float | None] = mapped_column(Float)
    calf_cm: Mapped[float | None] = mapped_column(Float)


class WaterLog(Base):
    """Plain drinking water, tracked separately from food."""
    __tablename__ = "water_logs"
    __table_args__ = (Index("ix_water_logs_user_id_drank_at", "user_id", "drank_at"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    amount_ml: Mapped[float] = mapped_column(Float)
    drank_at: Mapped[datetime] = mapped_column(UTCDateTime, index=True)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow)


class UserFood(Base):
    """A food in the user's personal library, or a saved recipe.

    Nutrients are stored for a reference amount (`ref_qty` `ref_unit`), e.g. 100 g,
    100 ml, 1 piece or 1 serving. Optional gram weights for a piece/serving let one
    record answer "3 almonds" and "30 g almonds" alike. Scaling is done in code
    (services/foods.py), so the LLM never does the arithmetic for known foods.
    """
    __tablename__ = "user_foods"
    __table_args__ = (UniqueConstraint("user_id", "name_key", name="uq_user_food_name"),
                      Index("ix_user_foods_user_id_last_used_at", "user_id", "last_used_at"))

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
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

    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow, onupdate=utcnow)
    last_used_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow)

    ingredients: Mapped[list["RecipeIngredient"]] = relationship(
        foreign_keys="RecipeIngredient.recipe_id",
        cascade="all, delete-orphan",
        order_by="RecipeIngredient.id",
    )


class RecipeIngredient(Base):
    __tablename__ = "recipe_ingredients"

    id: Mapped[int] = mapped_column(primary_key=True)
    recipe_id: Mapped[int] = mapped_column(ForeignKey("user_foods.id", ondelete="CASCADE"), index=True)
    # CASCADE matters only for account deletion: routers/foods.py refuses to delete an ingredient.
    food_id: Mapped[int] = mapped_column(ForeignKey("user_foods.id", ondelete="CASCADE"), index=True)
    quantity: Mapped[float] = mapped_column(Float)
    unit: Mapped[str] = mapped_column(String(32))

    food: Mapped[UserFood] = relationship(foreign_keys=[food_id])


class PendingAction(Base):
    """A write the LLM has proposed and the user has not yet confirmed."""
    __tablename__ = "pending_actions"
    __table_args__ = (Index("ix_pending_actions_user_id_status", "user_id", "status"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    action_type: Mapped[str] = mapped_column(String(16))           # create | edit | delete | save_recipe
    target_entry_id: Mapped[int | None] = mapped_column(ForeignKey("log_entries.id", ondelete="SET NULL"))
    payload: Mapped[dict] = mapped_column(JSON)
    # pending | confirmed | rejected | superseded | expired
    status: Mapped[str] = mapped_column(String(16), default="pending", index=True)
    chat_message_id: Mapped[int | None] = mapped_column(ForeignKey("chat_messages.id", ondelete="SET NULL"))
    result_entry_id: Mapped[int | None] = mapped_column(ForeignKey("log_entries.id", ondelete="SET NULL"))
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow)
    resolved_at: Mapped[datetime | None] = mapped_column(UTCDateTime)


class ChatMessage(Base):
    __tablename__ = "chat_messages"
    __table_args__ = (Index("ix_chat_messages_user_id_created_at", "user_id", "created_at"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    # user | assistant | event (event = app-generated note, e.g. "user confirmed #12")
    role: Mapped[str] = mapped_column(String(16))
    content: Mapped[str] = mapped_column(Text)
    kind: Mapped[str | None] = mapped_column(String(16))     # e.g. "progress" (day-so-far card)
    data: Mapped[dict | None] = mapped_column(JSON)          # structured data for that card
    related_log_entry_id: Mapped[int | None] = mapped_column(ForeignKey("log_entries.id", ondelete="SET NULL"))
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow, index=True)

    actions: Mapped[list[PendingAction]] = relationship(
        primaryjoin="ChatMessage.id == PendingAction.chat_message_id",
        order_by="PendingAction.id",
        viewonly=True,
    )


class AiRequest(Base):
    """One row per request the AI answered for a user (a chat message or a Dashboard estimate),
    for the daily allowance. Written in the same transaction as the reply, so failed or stopped
    requests don't count."""
    __tablename__ = "ai_requests"
    __table_args__ = (Index("ix_ai_requests_user_id_created_at", "user_id", "created_at"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow, index=True)
    kind: Mapped[str] = mapped_column(String(20))           # chat | dashboard_add


class PasswordReset(Base):
    """A "forgot password" link. Only a hash of the token is stored; it works once, for a short time."""
    __tablename__ = "password_resets"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow)
    expires_at: Mapped[datetime] = mapped_column(UTCDateTime)
    used_at: Mapped[datetime | None] = mapped_column(UTCDateTime)
