"""refine_debt_reference_types

Revision ID: 9b2d4f7a1c6e
Revises: 8f3a6c1b9d2e
Create Date: 2026-05-06 17:55:00.000000

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "9b2d4f7a1c6e"
down_revision: Union[str, Sequence[str], None] = "8f3a6c1b9d2e"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        UPDATE transactions AS t
        SET reference_type = 'debt_expense'
        FROM debts AS d
        WHERE t.debt_id = d.id
          AND d.is_money_transferred = FALSE
          AND t.transaction_type = 'EXPENSE'
          AND t.reference_type = 'debt_charge'
        """
    )

    op.execute(
        """
        UPDATE transactions AS t
        SET reference_type = 'debt_income'
        FROM debts AS d
        WHERE t.debt_id = d.id
          AND d.is_money_transferred = FALSE
          AND t.transaction_type = 'INCOME'
          AND t.reference_type = 'debt_charge'
        """
    )


def downgrade() -> None:
    op.execute(
        """
        UPDATE transactions
        SET reference_type = 'debt_charge'
        WHERE reference_type IN ('debt_expense', 'debt_income')
        """
    )
