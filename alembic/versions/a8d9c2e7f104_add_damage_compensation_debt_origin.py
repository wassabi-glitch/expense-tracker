"""add damage compensation debt origin

Revision ID: a8d9c2e7f104
Revises: f6a7b8c9d0e1
Create Date: 2026-06-03 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op


revision: str = "a8d9c2e7f104"
down_revision: Union[str, Sequence[str], None] = "f6a7b8c9d0e1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.execute("ALTER TYPE debtoriginkind ADD VALUE IF NOT EXISTS 'DAMAGE_COMPENSATION'")


def downgrade() -> None:
    # PostgreSQL enum values cannot be removed safely without recreating the type.
    pass
