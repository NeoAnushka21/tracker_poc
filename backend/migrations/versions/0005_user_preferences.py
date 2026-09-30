"""user preferences (optional "about you" answers)

Revision ID: 0005
Revises: 0004
Create Date: 2026-09-30
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "0005"
down_revision: Union[str, Sequence[str], None] = "0004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "user_preferences",
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("diet_type", sa.String(length=16), nullable=True),
        sa.Column("allergies", sa.JSON(), nullable=True),
        sa.Column("allergy_notes", sa.String(length=200), nullable=True),
        sa.Column("pace_kg_per_week", sa.Float(), nullable=True),
        sa.Column("breakfast_time", sa.String(length=5), nullable=True),
        sa.Column("lunch_time", sa.String(length=5), nullable=True),
        sa.Column("dinner_time", sa.String(length=5), nullable=True),
        sa.Column("training_days", sa.JSON(), nullable=True),
        sa.Column("training_type", sa.String(length=16), nullable=True),
        sa.Column("health_conditions", sa.JSON(), nullable=True),
        sa.Column("pregnancy", sa.String(length=16), nullable=True),
        sa.Column("health_consent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("skipped_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], name="fk_user_preferences_user_id_users",
                                ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("user_id", name="pk_user_preferences"),
    )


def downgrade() -> None:
    op.drop_table("user_preferences")
