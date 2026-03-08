"""add business work to expensecategory enum

Revision ID: 4e856246e7b7
Revises: 4f52c8c3398a
Create Date: 2026-03-07 23:01:16.856733

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '4e856246e7b7'
down_revision: Union[str, Sequence[str], None] = '4f52c8c3398a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.execute("ALTER TYPE expensecategory ADD VALUE 'BUSINESS_WORK';")


def downgrade() -> None:
    """Downgrade schema."""
    pass
