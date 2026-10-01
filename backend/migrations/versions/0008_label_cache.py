"""label_cache (Open Food Facts searches and labels, public data, shared)

Revision ID: 0008
Revises: 0007
Create Date: 2026-10-01
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0008"
down_revision: Union[str, Sequence[str], None] = "0007"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "label_cache",
        sa.Column("key", sa.String(length=300), nullable=False),
        sa.Column("labels", sa.JSON(), nullable=False),
        sa.Column("fetched_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("key", name="pk_label_cache"),
    )


def downgrade() -> None:
    op.drop_table("label_cache")
