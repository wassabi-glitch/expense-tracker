"""backfill_budgets_and_expenses

Revision ID: 799f8b552bf7
Revises: a7b4c2bc45f4
Create Date: 2026-02-28 09:05:04.262728

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '799f8b552bf7'
down_revision: Union[str, Sequence[str], None] = 'a7b4c2bc45f4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # 1. Backfill missing budgets for historical expenses using the latest known budget limit
    op.execute("""
        WITH expense_months AS (
            SELECT DISTINCT owner_id, category, EXTRACT(YEAR FROM date)::int AS exp_year, EXTRACT(MONTH FROM date)::int AS exp_month
            FROM expenses
        ),
        latest_budgets AS (
            SELECT DISTINCT ON (owner_id, category) owner_id, category, monthly_limit
            FROM budgets
            ORDER BY owner_id, category, budget_year DESC, budget_month DESC
        ),
        missing_budgets AS (
            SELECT em.owner_id, em.category, lb.monthly_limit, em.exp_year, em.exp_month
            FROM expense_months em
            JOIN latest_budgets lb ON lb.owner_id = em.owner_id AND lb.category = em.category
            LEFT JOIN budgets b ON b.owner_id = em.owner_id AND b.category = em.category AND b.budget_year = em.exp_year AND b.budget_month = em.exp_month
            WHERE b.id IS NULL
        )
        INSERT INTO budgets (owner_id, category, monthly_limit, budget_year, budget_month)
        SELECT owner_id, category, monthly_limit, exp_year, exp_month
        FROM missing_budgets;
    """)

    # 2. Link expenses to their corresponding monthly budgets
    op.execute("""
        UPDATE expenses e
        SET budget_id = b.id
        FROM budgets b
        WHERE e.owner_id = b.owner_id
          AND e.category = b.category
          AND EXTRACT(YEAR FROM e.date)::int = b.budget_year
          AND EXTRACT(MONTH FROM e.date)::int = b.budget_month
          AND e.budget_id IS NULL;
    """)


def downgrade() -> None:
    """Downgrade schema."""
    # Unlink expenses. We intentionally do not delete cloned budgets here as users might have legitimately used/edited them.
    op.execute("UPDATE expenses SET budget_id = NULL;")
