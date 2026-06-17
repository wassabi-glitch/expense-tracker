"""add_new_expense_categories_v3

Revision ID: 9a9df9b0aece
Revises: 12f2080d6dd6
Create Date: 2026-04-17 09:23:45.134437

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '9a9df9b0aece'
down_revision: Union[str, Sequence[str], None] = '12f2080d6dd6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # We use IF NOT EXISTS to prevent errors if the migration is re-run or partially applied.
    # Postgres 15 supports IF NOT EXISTS for ADD VALUE.
    op.execute("ALTER TYPE expensecategory ADD VALUE IF NOT EXISTS 'BANK_FEES_INTEREST'")
    op.execute("ALTER TYPE expensecategory ADD VALUE IF NOT EXISTS 'TRAVEL'")
    op.execute("ALTER TYPE expensecategory ADD VALUE IF NOT EXISTS 'CHARITY'")
    op.execute("ALTER TYPE expensecategory ADD VALUE IF NOT EXISTS 'ANIMALS_PETS'")


def downgrade() -> None:
    """Downgrade schema."""
    # Postgres does not easily support removing ENUM values.
    # Typically, we leave them as they don't affect existing data.
    pass
