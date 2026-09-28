"""Account deletion: remove a user and everything they logged."""
from sqlalchemy import delete, select, update
from sqlalchemy.orm import Session

from app.models import (
    AdminAudit, BodyMeasurement, ChatMessage, LlmUsage, LogEntry, LogEntryItem, PendingAction, RecipeIngredient, User, UserFood,
    UserTarget, WaterLog, WeightLog,
)


def delete_user_and_data(db: Session, user: User) -> None:
    uid = user.id
    entry_ids = select(LogEntry.id).where(LogEntry.user_id == uid)
    food_ids = select(UserFood.id).where(UserFood.user_id == uid)

    # Order matters: children before the rows they point at.
    db.execute(delete(PendingAction).where(PendingAction.user_id == uid))
    db.execute(delete(ChatMessage).where(ChatMessage.user_id == uid))
    db.execute(delete(LogEntryItem).where(LogEntryItem.log_entry_id.in_(entry_ids)))
    db.execute(delete(LogEntry).where(LogEntry.user_id == uid))
    db.execute(delete(RecipeIngredient).where(RecipeIngredient.recipe_id.in_(food_ids)))
    db.execute(delete(UserFood).where(UserFood.user_id == uid))
    db.execute(delete(WaterLog).where(WaterLog.user_id == uid))
    db.execute(delete(WeightLog).where(WeightLog.user_id == uid))
    db.execute(delete(BodyMeasurement).where(BodyMeasurement.user_id == uid))
    db.execute(delete(UserTarget).where(UserTarget.user_id == uid))
    # Keep the admin audit trail, but unlink it from the deleted account.
    db.execute(update(AdminAudit).where(AdminAudit.target_user_id == uid).values(target_user_id=None))
    # Model usage counts are quota history, not personal data: keep them, anonymised.
    db.execute(update(LlmUsage).where(LlmUsage.user_id == uid).values(user_id=None))
    db.execute(delete(User).where(User.id == uid))
    db.commit()
