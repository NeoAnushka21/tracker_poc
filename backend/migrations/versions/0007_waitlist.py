"""waitlist ("Join the community" sign-ups while sign-up is by invitation)

Revision ID: 0007
Revises: 0006
Create Date: 2026-10-01
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0007"
down_revision: Union[str, Sequence[str], None] = "0006"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "waitlist",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("public_id", sa.Uuid(), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("name", sa.String(length=80), nullable=False),
        sa.Column("interest", sa.String(length=300), nullable=True),
        sa.Column("consent_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id", name="pk_waitlist"),
        sa.UniqueConstraint("public_id", name="uq_waitlist_public_id"),
    )
    with op.batch_alter_table("waitlist") as b:
        b.create_index("ix_waitlist_email", ["email"], unique=True)


def downgrade() -> None:
    with op.batch_alter_table("waitlist") as b:
        b.drop_index("ix_waitlist_email")
    op.drop_table("waitlist")
