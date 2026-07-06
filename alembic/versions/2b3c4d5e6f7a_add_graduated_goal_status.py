"""add graduated goal status

Revision ID: 2b3c4d5e6f7a
Revises: ff8b9c0d1e23
Create Date: 2026-07-06 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "2b3c4d5e6f7a"
down_revision: Union[str, Sequence[str], None] = "ff8b9c0d1e23"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        with op.get_context().autocommit_block():
            op.execute(sa.text("ALTER TYPE goalstatus ADD VALUE IF NOT EXISTS 'GRADUATED'"))


def downgrade() -> None:
    # PostgreSQL enum value removal requires type recreation and data migration.
    # Keep downgrade as a no-op to avoid corrupting historical graduated goals.
    pass
