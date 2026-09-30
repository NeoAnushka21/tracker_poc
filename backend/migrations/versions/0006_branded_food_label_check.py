"""branded foods: label check

`label_checked` is true once a saved food's numbers come from its pack label (picked from
Open Food Facts, or typed in by the user). `off_code` is the Open Food Facts barcode it
was matched to, if any.

Revision ID: 0006
Revises: 0005
Create Date: 2026-09-30
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0006"
down_revision: Union[str, Sequence[str], None] = "0005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("user_foods") as b:
        b.add_column(sa.Column("label_checked", sa.Boolean(), nullable=False, server_default=sa.false()))
        b.add_column(sa.Column("off_code", sa.String(length=32), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("user_foods") as b:
        b.drop_column("off_code")
        b.drop_column("label_checked")
