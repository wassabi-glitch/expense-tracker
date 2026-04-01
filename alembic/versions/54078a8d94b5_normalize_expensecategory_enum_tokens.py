"""normalize_expensecategory_enum_tokens

Revision ID: 54078a8d94b5
Revises: 557aa2e9f51b
Create Date: 2026-04-01 13:37:20.487027

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '54078a8d94b5'
down_revision: Union[str, Sequence[str], None] = '557aa2e9f51b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Normalize expensecategory enum values to canonical UPPER_SNAKE tokens."""
    op.execute(
        """
        ALTER TYPE expensecategory RENAME TO expensecategory_old;
        """
    )

    op.execute(
        """
        CREATE TYPE expensecategory AS ENUM (
          'GROCERIES',
          'DINING_OUT',
          'HOUSING',
          'UTILITIES',
          'SUBSCRIPTIONS',
          'TRANSPORT',
          'HEALTH',
          'EDUCATION',
          'CLOTHING',
          'FAMILY_EVENTS',
          'ENTERTAINMENT',
          'INSTALLMENTS_DEBT',
          'BUSINESS_WORK',
          'ELECTRONICS',
          'PERSONAL_CARE'
        );
        """
    )

    op.execute(
        """
        ALTER TABLE IF EXISTS expenses
          ALTER COLUMN category TYPE expensecategory
          USING (
            CASE category::text
              WHEN 'Groceries' THEN 'GROCERIES'
              WHEN 'Dining Out' THEN 'DINING_OUT'
              WHEN 'Housing' THEN 'HOUSING'
              WHEN 'Utilities' THEN 'UTILITIES'
              WHEN 'Subscriptions' THEN 'SUBSCRIPTIONS'
              WHEN 'Transport' THEN 'TRANSPORT'
              WHEN 'Health' THEN 'HEALTH'
              WHEN 'Education' THEN 'EDUCATION'
              WHEN 'Clothing' THEN 'CLOTHING'
              WHEN 'Family & Events' THEN 'FAMILY_EVENTS'
              WHEN 'Entertainment' THEN 'ENTERTAINMENT'
              WHEN 'Installments & Debt' THEN 'INSTALLMENTS_DEBT'
              WHEN 'Business / Work' THEN 'BUSINESS_WORK'
              WHEN 'Electronics' THEN 'ELECTRONICS'
              WHEN 'Personal care' THEN 'PERSONAL_CARE'
              ELSE category::text
            END
          )::expensecategory;
        """
    )

    op.execute(
        """
        ALTER TABLE IF EXISTS budgets
          ALTER COLUMN category TYPE expensecategory
          USING (
            CASE category::text
              WHEN 'Groceries' THEN 'GROCERIES'
              WHEN 'Dining Out' THEN 'DINING_OUT'
              WHEN 'Housing' THEN 'HOUSING'
              WHEN 'Utilities' THEN 'UTILITIES'
              WHEN 'Subscriptions' THEN 'SUBSCRIPTIONS'
              WHEN 'Transport' THEN 'TRANSPORT'
              WHEN 'Health' THEN 'HEALTH'
              WHEN 'Education' THEN 'EDUCATION'
              WHEN 'Clothing' THEN 'CLOTHING'
              WHEN 'Family & Events' THEN 'FAMILY_EVENTS'
              WHEN 'Entertainment' THEN 'ENTERTAINMENT'
              WHEN 'Installments & Debt' THEN 'INSTALLMENTS_DEBT'
              WHEN 'Business / Work' THEN 'BUSINESS_WORK'
              WHEN 'Electronics' THEN 'ELECTRONICS'
              WHEN 'Personal care' THEN 'PERSONAL_CARE'
              ELSE category::text
            END
          )::expensecategory;
        """
    )

    op.execute(
        """
        ALTER TABLE IF EXISTS recurring_expenses
          ALTER COLUMN category TYPE expensecategory
          USING (
            CASE category::text
              WHEN 'Groceries' THEN 'GROCERIES'
              WHEN 'Dining Out' THEN 'DINING_OUT'
              WHEN 'Housing' THEN 'HOUSING'
              WHEN 'Utilities' THEN 'UTILITIES'
              WHEN 'Subscriptions' THEN 'SUBSCRIPTIONS'
              WHEN 'Transport' THEN 'TRANSPORT'
              WHEN 'Health' THEN 'HEALTH'
              WHEN 'Education' THEN 'EDUCATION'
              WHEN 'Clothing' THEN 'CLOTHING'
              WHEN 'Family & Events' THEN 'FAMILY_EVENTS'
              WHEN 'Entertainment' THEN 'ENTERTAINMENT'
              WHEN 'Installments & Debt' THEN 'INSTALLMENTS_DEBT'
              WHEN 'Business / Work' THEN 'BUSINESS_WORK'
              WHEN 'Electronics' THEN 'ELECTRONICS'
              WHEN 'Personal care' THEN 'PERSONAL_CARE'
              ELSE category::text
            END
          )::expensecategory;
        """
    )

    op.execute(
        """
        DROP TYPE expensecategory_old;
        """
    )


def downgrade() -> None:
    """Downgrade is intentionally omitted for enum normalization migration."""
    raise NotImplementedError("Downgrade is not supported for this enum normalization migration.")
