"""add last_notified_threshold to budgets

Revision ID: 557aa2e9f51b
Revises: a1b2c3d4e5f6
Create Date: 2026-03-19 11:50:03.506614

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '557aa2e9f51b'
down_revision: Union[str, Sequence[str], None] = 'a1b2c3d4e5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('budgets', sa.Column('last_notified_threshold', sa.Integer(), nullable=False, server_default='0'))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('budgets', 'last_notified_threshold')
