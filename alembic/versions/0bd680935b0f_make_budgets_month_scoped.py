"""make budgets month scoped

Revision ID: 0bd680935b0f
Revises: b4ce74108239
Create Date: 2026-02-26 05:22:21.995246

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0bd680935b0f'
down_revision: Union[str, Sequence[str], None] = 'b4ce74108239'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1) Add new columns as nullable
    op.add_column("budgets", sa.Column(
        "budget_year", sa.Integer(), nullable=True))
    op.add_column("budgets", sa.Column(
        "budget_month", sa.Integer(), nullable=True))

    # 2) Backfill from database current date (Postgres)
    op.execute(
        """
        UPDATE budgets
        SET budget_year = EXTRACT(YEAR FROM CURRENT_DATE)::int
        WHERE budget_year IS NULL
        """
    )
    op.execute(
        """
        UPDATE budgets
        SET budget_month = EXTRACT(MONTH FROM CURRENT_DATE)::int
        WHERE budget_month IS NULL
        """
    )

    # 3) Make non-null
    op.alter_column("budgets", "budget_year", nullable=False)
    op.alter_column("budgets", "budget_month", nullable=False)

    # 4) Add constraints/indexes
    op.create_check_constraint(
        "ck_budgets_budget_month_1_12",
        "budgets",
        "budget_month >= 1 AND budget_month <= 12",
    )

    op.create_check_constraint(
        "ck_budgets_budget_year_min_2020",
        "budgets",
        "budget_year >= 2020",
    )

    op.create_index(
        "ix_budgets_owner_year_month",
        "budgets",
        ["owner_id", "budget_year", "budget_month"],
        unique=False,
    )

    op.create_unique_constraint(
        "uq_budgets_owner_category_year_month",
        "budgets",
        ["owner_id", "category", "budget_year", "budget_month"],
    )

    # 5) Drop redundant columns
    op.drop_column("budgets", "last_notified_month")
    op.drop_column("budgets", "last_notified_year")
    op.drop_column("budgets", "is_active")


def downgrade() -> None:
    # 1) Add back dropped columns as nullable first
    op.add_column("budgets", sa.Column(
        "last_notified_month", sa.Integer(), nullable=True))
    op.add_column("budgets", sa.Column(
        "last_notified_year", sa.Integer(), nullable=True))
    op.add_column("budgets", sa.Column(
        "is_active", sa.Boolean(), nullable=True))

    # 2) Backfill from budget row scope (best-effort)
    op.execute(
        "UPDATE budgets SET last_notified_month = budget_month WHERE last_notified_month IS NULL")
    op.execute(
        "UPDATE budgets SET last_notified_year = budget_year WHERE last_notified_year IS NULL")
    op.execute("UPDATE budgets SET is_active = TRUE WHERE is_active IS NULL")

    # 3) Restore non-null
    op.alter_column("budgets", "last_notified_month", nullable=False)
    op.alter_column("budgets", "last_notified_year", nullable=False)
    op.alter_column("budgets", "is_active", nullable=False)

    # 4) Drop new constraints/indexes
    op.drop_constraint("uq_budgets_owner_category_year_month",
                       "budgets", type_="unique")
    op.drop_index("ix_budgets_owner_year_month", table_name="budgets")
    op.drop_constraint("ck_budgets_budget_month_1_12",
                       "budgets", type_="check")
    op.drop_constraint("ck_budgets_budget_year_min_2020",
                       "budgets", type_="check")

    # 5) Drop new columns
    op.drop_column("budgets", "budget_month")
    op.drop_column("budgets", "budget_year")
