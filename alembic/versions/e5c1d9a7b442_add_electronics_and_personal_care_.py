"""add electronics and personal care to expensecategory enum

Revision ID: e5c1d9a7b442
Revises: ab4d9f1c22b7
Create Date: 2026-03-12 23:40:00.000000

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = 'e5c1d9a7b442'
down_revision: Union[str, Sequence[str], None] = 'ab4d9f1c22b7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("ALTER TYPE expensecategory ADD VALUE 'ELECTRONICS';")
    op.execute("ALTER TYPE expensecategory ADD VALUE 'PERSONAL_CARE';")


def downgrade() -> None:
    pass
