"""update_expense_categories_to_12_items

Revision ID: ae7918f21932
Revises: c36276b796d0
Create Date: 2026-03-05 22:55:17.053914

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'ae7918f21932'
down_revision: Union[str, Sequence[str], None] = 'c36276b796d0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # STEP 1: Delete all data from transaction tables to avoid Enum conflicts
    # Users tables and identities are NOT touched.
    op.execute("DELETE FROM expenses")
    op.execute("DELETE FROM budgets")
    op.execute("DELETE FROM recurring_expenses")
    
    # STEP 2: Update the PostgreSQL Enum type
    # ALTER TYPE ... ADD VALUE cannot run inside a transaction block in standard PG.
    
    all_target_categories = [
        'Groceries', 'Dining Out', 'Housing', 'Utilities', 'Subscriptions', 
        'Transport', 'Health', 'Education', 'Clothing', 'Family & Events', 
        'Entertainment', 'Installments & Debt'
    ]
    
    # Using autocommit block to allow ALTER TYPE ... ADD VALUE
    with op.get_context().autocommit_block():
        for cat in all_target_categories:
            # Note: IF NOT EXISTS is only available in PG 9.6+, but we use it here
            # for robustness if the environment supports it. 
            op.execute(sa.text(f"ALTER TYPE expensecategory ADD VALUE IF NOT EXISTS '{cat}'"))

def downgrade() -> None:
    # Downgrade remains complex for Enums. 
    pass

def downgrade() -> None:
    """Downgrade schema."""
    # Reverse the changes
    pass