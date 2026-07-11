"""add_archived_at_to_payment_plans

Revision ID: a33848128f13
Revises: 02458023e9dc
Create Date: 2026-07-11 05:33:53.660282

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'a33848128f13'
down_revision: Union[str, Sequence[str], None] = '02458023e9dc'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "payment_plans",
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("payment_plans", "archived_at")
