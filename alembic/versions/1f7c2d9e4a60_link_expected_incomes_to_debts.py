"""link expected incomes to debts

Revision ID: 1f7c2d9e4a60
Revises: 0f4e9c8d7b6a
Create Date: 2026-06-14 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "1f7c2d9e4a60"
down_revision: Union[str, Sequence[str], None] = "0f4e9c8d7b6a"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("expected_incomes", sa.Column("debt_id", sa.Integer(), nullable=True))
    op.add_column("expected_incomes", sa.Column("received_amount", sa.BigInteger(), nullable=True))
    op.add_column("expected_incomes", sa.Column("linked_transaction_id", sa.Integer(), nullable=True))
    op.create_foreign_key(
        "fk_expected_incomes_debt_id_debts",
        "expected_incomes",
        "debts",
        ["debt_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_foreign_key(
        "fk_expected_incomes_linked_transaction_id_financial_events",
        "expected_incomes",
        "financial_events",
        ["linked_transaction_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(op.f("ix_expected_incomes_debt_id"), "expected_incomes", ["debt_id"], unique=False)
    op.create_index(
        op.f("ix_expected_incomes_linked_transaction_id"),
        "expected_incomes",
        ["linked_transaction_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_expected_incomes_linked_transaction_id"), table_name="expected_incomes")
    op.drop_index(op.f("ix_expected_incomes_debt_id"), table_name="expected_incomes")
    op.drop_constraint(
        "fk_expected_incomes_linked_transaction_id_financial_events",
        "expected_incomes",
        type_="foreignkey",
    )
    op.drop_constraint("fk_expected_incomes_debt_id_debts", "expected_incomes", type_="foreignkey")
    op.drop_column("expected_incomes", "linked_transaction_id")
    op.drop_column("expected_incomes", "received_amount")
    op.drop_column("expected_incomes", "debt_id")
