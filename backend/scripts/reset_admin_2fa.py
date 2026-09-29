"""Turn off two-step sign-in for an admin who lost their authenticator (run by the owner).

    cd backend
    set DATABASE_URL=<the database to change, e.g. the Neon connection string>
    .venv\\Scripts\\python scripts\\reset_admin_2fa.py mhatre.anushka.work@gmail.com

The admin then logs in with the password only and can set two-step sign-in up again.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.db import SessionLocal  # noqa: E402
from app.models import User  # noqa: E402


def main(email: str) -> None:
    with SessionLocal() as db:
        user = db.query(User).filter(User.email == email.strip().lower()).first()
        if user is None:
            sys.exit(f"No account {email}")
        user.totp_secret = user.totp_enabled_at = user.totp_last_step = None
        db.commit()
        print(f"Two-step sign-in is off for {user.email}.")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit("Usage: python scripts/reset_admin_2fa.py <admin email>")
    main(sys.argv[1])
