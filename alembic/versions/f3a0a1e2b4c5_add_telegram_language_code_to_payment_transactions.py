"""add_telegram_language_code_to_payment_transactions

Revision ID: f3a0a1e2b4c5
Revises: d1b7f5d6f9a1
Create Date: 2026-03-16

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "f3a0a1e2b4c5"
down_revision: Union[str, Sequence[str], None] = "d1b7f5d6f9a1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("payment_transactions", sa.Column("telegram_language_code", sa.String(length=10), nullable=True))


def downgrade() -> None:
    op.drop_column("payment_transactions", "telegram_language_code")

