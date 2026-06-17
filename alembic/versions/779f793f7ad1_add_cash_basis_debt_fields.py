"""add_cash_basis_debt_fields

Revision ID: 779f793f7ad1
Revises: 72ae18a4a835
Create Date: 2026-05-03 07:33:47.741776

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '779f793f7ad1'
down_revision: Union[str, Sequence[str], None] = '72ae18a4a835'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Add new Enum value
    op.execute("ALTER TYPE transactiontype ADD VALUE IF NOT EXISTS 'DEBT_TRANSFER'")

    op.add_column('debts', sa.Column('expense_category', sa.Enum('GROCERIES', 'DINING_OUT', 'ELECTRONICS', 'HOUSING', 'UTILITIES', 'SUBSCRIPTIONS', 'TRANSPORT', 'HEALTH', 'PERSONAL_CARE', 'EDUCATION', 'CLOTHING', 'FAMILY_EVENTS', 'ENTERTAINMENT', 'INSTALLMENTS_DEBT', 'BUSINESS_WORK', 'BANK_FEES_INTEREST', 'TRAVEL', 'CHARITY', 'ANIMALS_PETS', name='expensecategory'), nullable=True))
    op.add_column('debts', sa.Column('income_source_id', sa.Integer(), nullable=True))
    op.create_foreign_key(None, 'debts', 'income_sources', ['income_source_id'], ['id'], ondelete='SET NULL')
    
    op.add_column('transactions', sa.Column('debt_id', sa.Integer(), nullable=True))
    op.create_foreign_key(None, 'transactions', 'debts', ['debt_id'], ['id'], ondelete='SET NULL')
    op.create_index(op.f('ix_transactions_debt_id'), 'transactions', ['debt_id'], unique=False)
    
    # Data Migration: move DEBT_PAYMENT reference_ids to the new debt_id column
    op.execute("UPDATE transactions SET debt_id = reference_id WHERE transaction_type = 'DEBT_PAYMENT'")


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_transactions_debt_id'), table_name='transactions')
    op.drop_constraint(None, 'transactions', type_='foreignkey')
    op.drop_column('transactions', 'debt_id')
    
    op.drop_constraint(None, 'debts', type_='foreignkey')
    op.drop_column('debts', 'income_source_id')
    op.drop_column('debts', 'expense_category')

