"""Account deletion: remove a user and everything they logged."""
from sqlalchemy import delete
from sqlalchemy.orm import Session

from app.models import User, WaitlistEntry


def delete_user_and_data(db: Session, user: User) -> None:
    """Deleting the user row removes everything they own through ON DELETE CASCADE (migration
    0003). Admin audit rows and model-usage rows are kept, unlinked (SET NULL): they're quota
    and oversight history, not personal data. Their waitlist row (matched by email, not linked)
    goes too. tests/test_privacy.py checks no row is left behind."""
    db.execute(delete(WaitlistEntry).where(WaitlistEntry.email == user.email))
    db.execute(delete(User).where(User.id == user.id))
    db.commit()
