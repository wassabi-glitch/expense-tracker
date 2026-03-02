"""add expense budget fk and drop budget alert threshold

Revision ID: 1bd1a26c2392
Revises: 61c6fc5a5fc6
Create Date: 2026-02-26 08:17:57.503648

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '1bd1a26c2392'
down_revision: Union[str, Sequence[str], None] = '61c6fc5a5fc6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add nullable FK first (we will backfill later in app/data migration)
    op.add_column("expenses", sa.Column(
        "budget_id", sa.Integer(), nullable=True))
    op.create_index("ix_expenses_budget_id", "expenses",
                    ["budget_id"], unique=False)
    op.create_foreign_key(
        "fk_expenses_budget_id_budgets",
        "expenses",
        "budgets",
        ["budget_id"],
        ["id"],
        ondelete="RESTRICT",
    )

    # Remove old budget alert memory column (notification system redesign)
    op.drop_column("budgets", "last_notified_threshold")


def downgrade() -> None:
    # Bring back old column safely
    op.add_column("budgets", sa.Column(
        "last_notified_threshold", sa.Integer(), nullable=True))
    op.execute(
        "UPDATE budgets SET last_notified_threshold = 0 WHERE last_notified_threshold IS NULL")
    op.alter_column("budgets", "last_notified_threshold", nullable=False)

    # Remove FK/index/column
    op.drop_constraint("fk_expenses_budget_id_budgets",
                       "expenses", type_="foreignkey")
    op.drop_index("ix_expenses_budget_id", table_name="expenses")
    op.drop_column("expenses", "budget_id")
