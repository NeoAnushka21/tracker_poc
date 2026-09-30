"""user country and region

Both nullable: new accounts must pick a country during onboarding (checked by the API), and
accounts from before this are asked once after signing in (`needs_location`).

Revision ID: 0004
Revises: 0003
Create Date: 2026-09-30
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0004"
down_revision: Union[str, Sequence[str], None] = "0003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("users") as b:
        b.add_column(sa.Column("country", sa.String(length=2), nullable=True))
        b.add_column(sa.Column("region", sa.String(length=80), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("users") as b:
        b.drop_column("region")
        b.drop_column("country")
