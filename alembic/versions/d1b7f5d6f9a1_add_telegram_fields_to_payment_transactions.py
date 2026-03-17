"""add_telegram_fields_to_payment_transactions

Revision ID: d1b7f5d6f9a1
Revises: c4e69a9f28ea
Create Date: 2026-03-16

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "d1b7f5d6f9a1"
down_revision: Union[str, Sequence[str], None] = "c4e69a9f28ea"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("payment_transactions", sa.Column("telegram_user_id", sa.BigInteger(), nullable=True))
    op.add_column("payment_transactions", sa.Column("telegram_chat_id", sa.BigInteger(), nullable=True))
    op.add_column("payment_transactions", sa.Column("telegram_receipt_message_id", sa.BigInteger(), nullable=True))
    op.add_column("payment_transactions", sa.Column("receipt_submitted_at", sa.DateTime(timezone=True), nullable=True))
    op.create_index(op.f("ix_payment_transactions_telegram_user_id"), "payment_transactions", ["telegram_user_id"], unique=False)
    op.create_index(op.f("ix_payment_transactions_telegram_chat_id"), "payment_transactions", ["telegram_chat_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_payment_transactions_telegram_chat_id"), table_name="payment_transactions")
    op.drop_index(op.f("ix_payment_transactions_telegram_user_id"), table_name="payment_transactions")
    op.drop_column("payment_transactions", "receipt_submitted_at")
    op.drop_column("payment_transactions", "telegram_receipt_message_id")
    op.drop_column("payment_transactions", "telegram_chat_id")
    op.drop_column("payment_transactions", "telegram_user_id")

