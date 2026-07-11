"""add_write_off_to_payment_plan_ledger_entry_type

Revision ID: 02458023e9dc
Revises: 7823c887d5fd
Create Date: 2026-07-11 04:36:30.625627

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '02458023e9dc'
down_revision: Union[str, Sequence[str], None] = '7823c887d5fd'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.execute("ALTER TYPE paymentplanledgerentrytype ADD VALUE IF NOT EXISTS 'WRITE_OFF'")


def downgrade() -> None:
    """Downgrade schema.

    PostgreSQL does not support removing values from enum types.
    This is a no-op; the value is harmless if left in place.
    """
    pass
