"""separate_principal_and_charges

Revision ID: 72ae18a4a835
Revises: 27e091443c89
Create Date: 2026-05-03 01:24:56.667030

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '72ae18a4a835'
down_revision: Union[str, Sequence[str], None] = '27e091443c89'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    
    # Data Migration: Deflate initial_amount by subtracting accrued charges
    # so that initial_amount strictly represents the Principal.
    op.execute("""
        UPDATE debts d
        SET initial_amount = initial_amount - (
            SELECT COALESCE(SUM(amount), 0)
            FROM debt_charges c
            WHERE c.debt_id = d.id
        )
    """)


def downgrade() -> None:
    """Downgrade schema."""
    # Data Migration: Re-inflate initial_amount with charges
    op.execute("""
        UPDATE debts d
        SET initial_amount = initial_amount + (
            SELECT COALESCE(SUM(amount), 0)
            FROM debt_charges c
            WHERE c.debt_id = d.id
        )
    """)
