"""eradicate_budget_rollovers

Revision ID: 6a7b8c9d0e12
Revises: 5f6a7b8c9d01
Create Date: 2026-06-19 17:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "6a7b8c9d0e12"
down_revision: Union[str, Sequence[str], None] = "5f6a7b8c9d01"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_column("budgets", "rollover_mode")
    op.drop_column("budgets", "max_rollover_amount")
    op.drop_column("user_profiles", "budget_rollover_enabled")


def downgrade() -> None:
    op.add_column("user_profiles", sa.Column("budget_rollover_enabled", sa.Boolean(), nullable=True))
    op.execute("UPDATE user_profiles SET budget_rollover_enabled = true")
    op.alter_column("user_profiles", "budget_rollover_enabled", nullable=False)
    op.add_column("budgets", sa.Column("max_rollover_amount", sa.BigInteger(), nullable=True))
    op.add_column("budgets", sa.Column("rollover_mode", sa.String(length=10), nullable=True))
