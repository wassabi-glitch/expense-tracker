"""add_income_source_to_transactions_and_debt_charges_category

Revision ID: c8d41f0a2b77
Revises: 9b2d4f7a1c6e
Create Date: 2026-05-07 11:40:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "c8d41f0a2b77"
down_revision: Union[str, Sequence[str], None] = "9b2d4f7a1c6e"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.get_context().autocommit_block():
        op.execute("ALTER TYPE expensecategory ADD VALUE IF NOT EXISTS 'DEBT_CHARGES'")

    op.add_column("transactions", sa.Column("income_source_id", sa.Integer(), nullable=True))
    op.create_index("ix_transactions_income_source_id", "transactions", ["income_source_id"], unique=False)
    op.create_foreign_key(
        "fk_transactions_income_source_id_income_sources",
        "transactions",
        "income_sources",
        ["income_source_id"],
        ["id"],
        ondelete="SET NULL",
    )

    op.execute(
        """
        UPDATE transactions
        SET income_source_id = reference_id
        WHERE transaction_type = 'INCOME'
          AND income_source_id IS NULL
          AND reference_id IS NOT NULL
        """
    )

    op.execute(
        """
        UPDATE transactions
        SET category = 'DEBT_CHARGES'
        WHERE transaction_type = 'EXPENSE'
          AND reference_type = 'debt_charge'
          AND debt_id IS NOT NULL
        """
    )


def downgrade() -> None:
    op.execute(
        """
        UPDATE transactions
        SET reference_id = COALESCE(reference_id, income_source_id)
        WHERE transaction_type = 'INCOME'
          AND income_source_id IS NOT NULL
        """
    )

    op.drop_constraint("fk_transactions_income_source_id_income_sources", "transactions", type_="foreignkey")
    op.drop_index("ix_transactions_income_source_id", table_name="transactions")
    op.drop_column("transactions", "income_source_id")
