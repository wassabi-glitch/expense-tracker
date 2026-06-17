"""expand projects lifecycle and periods

Revision ID: 5c91b9a4d3e2
Revises: 37b2b7dd91aa
Create Date: 2026-05-17 11:10:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "5c91b9a4d3e2"
down_revision: Union[str, Sequence[str], None] = "37b2b7dd91aa"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("ALTER TYPE projectstatus ADD VALUE IF NOT EXISTS 'STOPPED'")

    op.add_column("projects", sa.Column("start_date", sa.Date(), nullable=True))
    op.add_column("projects", sa.Column("target_end_date", sa.Date(), nullable=True))
    op.add_column("projects", sa.Column("completed_at", sa.Date(), nullable=True))

    op.execute("UPDATE projects SET start_date = created_at::date WHERE start_date IS NULL")
    op.alter_column("projects", "start_date", nullable=False)


def downgrade() -> None:
    op.drop_column("projects", "completed_at")
    op.drop_column("projects", "target_end_date")
    op.drop_column("projects", "start_date")
