"""fix_schema_inconsistencies

Revision ID: a7b4c2bc45f4
Revises: 1bd1a26c2392
Create Date: 2026-02-28 08:46:05.483169

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'a7b4c2bc45f4'
down_revision: Union[str, Sequence[str], None] = '1bd1a26c2392'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.alter_column('expenses', 'expense_category_enum', new_column_name='category')


def downgrade() -> None:
    """Downgrade schema."""
    op.alter_column('expenses', 'category', new_column_name='expense_category_enum')
