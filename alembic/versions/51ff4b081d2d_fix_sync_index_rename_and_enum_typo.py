"""fix: sync index rename and enum typo

Revision ID: 51ff4b081d2d
Revises: a1b2c3d4e5f7
Create Date: 2026-07-27 14:00:46.332149

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '51ff4b081d2d'
down_revision: Union[str, Sequence[str], None] = 'a1b2c3d4e5f7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.drop_index(
        op.f('ix_iso_proj_subcat_alloc_category_alloc_id'),
        table_name='isolated_project_subcategory_allocations',
    )
    op.create_index(
        op.f('ix_isolated_project_subcategory_allocations_category_allocation_id'),
        'isolated_project_subcategory_allocations',
        ['category_allocation_id'],
        unique=False,
    )
    # Rename the enum type: schemodel → schedulemodel (typo fix).
    # SQLAlchemy's autogenerate tries ALTER COLUMN … TYPE which fails
    # because Postgres doesn't know the new enum name yet. The fix is
    # a plain ALTER TYPE … RENAME TO on the existing enum.
    op.execute(
        "ALTER TYPE schemodel RENAME TO schedulemodel"
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.execute(
        "ALTER TYPE schedulemodel RENAME TO schemodel"
    )
    op.drop_index(
        op.f('ix_isolated_project_subcategory_allocations_category_allocation_id'),
        table_name='isolated_project_subcategory_allocations',
    )
    op.create_index(
        op.f('ix_iso_proj_subcat_alloc_category_alloc_id'),
        'isolated_project_subcategory_allocations',
        ['category_allocation_id'],
        unique=False,
    )
