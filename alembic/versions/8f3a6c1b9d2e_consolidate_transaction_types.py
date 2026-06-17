"""consolidate_transaction_types

Revision ID: 8f3a6c1b9d2e
Revises: 779f793f7ad1
Create Date: 2026-05-06 17:10:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "8f3a6c1b9d2e"
down_revision: Union[str, Sequence[str], None] = "779f793f7ad1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


NEW_TRANSACTIONTYPE_VALUES = (
    "EXPENSE",
    "INCOME",
    "TRANSFER",
    "REFUND",
    "ADJUSTMENT",
    "DEBT_SETTLEMENT",
    "NEUTRAL_FLOW",
)

OLD_TRANSACTIONTYPE_VALUES = (
    "EXPENSE",
    "INCOME",
    "TRANSFER",
    "FEE",
    "INTEREST",
    "REFUND",
    "ADJUSTMENT",
    "DEBT_PAYMENT",
    "INSTALLMENT_PAYMENT",
    "SAVINGS_DEPOSIT",
    "SAVINGS_WITHDRAWAL",
    "DEBT_TRANSFER",
)


def _enum_sql(type_name: str, values: tuple[str, ...]) -> str:
    joined = ", ".join(f"'{value}'" for value in values)
    return f"CREATE TYPE {type_name} AS ENUM ({joined})"


def upgrade() -> None:
    op.add_column("transactions", sa.Column("reference_type", sa.String(length=50), nullable=True))

    op.execute(
        """
        UPDATE transactions
        SET transaction_type = 'EXPENSE', reference_type = COALESCE(reference_type, 'bank_fee')
        WHERE transaction_type = 'FEE'
        """
    )
    op.execute(
        """
        UPDATE transactions
        SET transaction_type = 'EXPENSE', reference_type = COALESCE(reference_type, 'bank_interest')
        WHERE transaction_type = 'INTEREST'
        """
    )
    op.execute(
        """
        UPDATE transactions
        SET transaction_type = 'DEBT_TRANSFER', reference_type = COALESCE(reference_type, 'debt_initial')
        WHERE transaction_type = 'DEBT_TRANSFER'
        """
    )
    op.execute(
        """
        UPDATE transactions
        SET transaction_type = 'DEBT_PAYMENT', reference_type = COALESCE(reference_type, 'debt_repayment')
        WHERE transaction_type = 'DEBT_PAYMENT'
        """
    )
    op.execute(
        """
        UPDATE transactions
        SET transaction_type = 'INSTALLMENT_PAYMENT', reference_type = COALESCE(reference_type, 'installment')
        WHERE transaction_type = 'INSTALLMENT_PAYMENT'
        """
    )
    op.execute(
        """
        UPDATE transactions
        SET transaction_type = 'SAVINGS_DEPOSIT', reference_type = COALESCE(reference_type, 'savings_deposit')
        WHERE transaction_type = 'SAVINGS_DEPOSIT'
        """
    )
    op.execute(
        """
        UPDATE transactions
        SET transaction_type = 'SAVINGS_WITHDRAWAL', reference_type = COALESCE(reference_type, 'savings_withdrawal')
        WHERE transaction_type = 'SAVINGS_WITHDRAWAL'
        """
    )

    op.execute(_enum_sql("transactiontype_new", NEW_TRANSACTIONTYPE_VALUES))
    op.execute(
        """
        ALTER TABLE transactions
        ALTER COLUMN transaction_type TYPE transactiontype_new
        USING (
            CASE
                WHEN transaction_type::text IN ('FEE', 'INTEREST', 'INSTALLMENT_PAYMENT') THEN 'EXPENSE'
                WHEN transaction_type::text IN ('DEBT_TRANSFER', 'DEBT_PAYMENT') THEN 'DEBT_SETTLEMENT'
                WHEN transaction_type::text IN ('SAVINGS_DEPOSIT', 'SAVINGS_WITHDRAWAL') THEN 'TRANSFER'
                ELSE transaction_type::text
            END
        )::transactiontype_new
        """
    )
    op.execute("DROP TYPE transactiontype")
    op.execute("ALTER TYPE transactiontype_new RENAME TO transactiontype")


def downgrade() -> None:
    # Best-effort mapping back to the pre-consolidation enum shape.
    op.execute(
        """
        UPDATE transactions
        SET transaction_type = CASE
            WHEN transaction_type = 'EXPENSE' AND reference_type = 'bank_fee' THEN 'FEE'
            WHEN transaction_type = 'EXPENSE' AND reference_type = 'bank_interest' THEN 'INTEREST'
            WHEN transaction_type = 'DEBT_SETTLEMENT' AND reference_type = 'debt_initial' THEN 'DEBT_TRANSFER'
            WHEN transaction_type = 'DEBT_SETTLEMENT' AND reference_type = 'debt_repayment' THEN 'DEBT_PAYMENT'
            WHEN transaction_type = 'DEBT_SETTLEMENT' THEN 'DEBT_PAYMENT'
            WHEN transaction_type = 'EXPENSE' AND reference_type = 'installment' THEN 'INSTALLMENT_PAYMENT'
            WHEN transaction_type = 'TRANSFER' AND reference_type = 'savings_deposit' THEN 'SAVINGS_DEPOSIT'
            WHEN transaction_type = 'TRANSFER' AND reference_type = 'savings_withdrawal' THEN 'SAVINGS_WITHDRAWAL'
            WHEN transaction_type = 'NEUTRAL_FLOW' THEN 'TRANSFER'
            ELSE transaction_type
        END
        """
    )

    op.execute(_enum_sql("transactiontype_old", OLD_TRANSACTIONTYPE_VALUES))
    op.execute(
        """
        ALTER TABLE transactions
        ALTER COLUMN transaction_type TYPE transactiontype_old
        USING transaction_type::text::transactiontype_old
        """
    )
    op.execute("DROP TYPE transactiontype")
    op.execute("ALTER TYPE transactiontype_old RENAME TO transactiontype")

    op.drop_column("transactions", "reference_type")
