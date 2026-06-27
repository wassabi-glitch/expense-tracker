"""add debt archive metadata

Revision ID: a32b1c2d3e4f
Revises: f9c0d1e2f3a4
Create Date: 2026-06-27 00:00:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "a32b1c2d3e4f"
down_revision: Union[str, Sequence[str], None] = "f9c0d1e2f3a4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("debts", sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True))
    op.create_index("ix_debts_owner_archived_at", "debts", ["owner_id", "archived_at"], unique=False)
    op.execute("UPDATE debts SET archived_at = NOW() WHERE status = 'ARCHIVED' AND archived_at IS NULL")


def downgrade() -> None:
    op.drop_index("ix_debts_owner_archived_at", table_name="debts")
    op.drop_column("debts", "archived_at")
