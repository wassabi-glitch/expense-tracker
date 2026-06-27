"""rename payment plan event index

Revision ID: f8b9c0d1e2f3
Revises: f7a8b9c0d1e2
Create Date: 2026-06-26 00:05:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "f8b9c0d1e2f3"
down_revision: Union[str, Sequence[str], None] = "f7a8b9c0d1e2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _rename_index(old: str, new: str) -> None:
    op.execute(sa.text(f'ALTER INDEX IF EXISTS "{old}" RENAME TO "{new}"'))


def upgrade() -> None:
    if op.get_bind().dialect.name == "postgresql":
        _rename_index("ix_installment_payments_event_id", "ix_payment_plan_payments_event_id")


def downgrade() -> None:
    if op.get_bind().dialect.name == "postgresql":
        _rename_index("ix_payment_plan_payments_event_id", "ix_installment_payments_event_id")
