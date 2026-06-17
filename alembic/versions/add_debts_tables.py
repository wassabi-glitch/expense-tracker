"""add debts and debt_payments tables

Revision ID: add_debts_tables
Revises: 54078a8d94b5
Create Date: 2026-04-08 03:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'add_debts_tables'
down_revision: Union[str, Sequence[str], None] = '54078a8d94b5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Create debts table using raw SQL (enum types already exist)
    op.execute("""
        CREATE TABLE debts (
            id SERIAL PRIMARY KEY,
            owner_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            debt_type debttype NOT NULL,
            creditor_name VARCHAR(100) NOT NULL,
            title VARCHAR(100) NOT NULL,
            total_amount BIGINT NOT NULL,
            paid_amount BIGINT NOT NULL DEFAULT 0,
            currency VARCHAR(3) NOT NULL DEFAULT 'UZS',
            description TEXT,
            status debtstatus NOT NULL DEFAULT 'ACTIVE',
            start_date DATE NOT NULL,
            due_date DATE,
            is_installment_plan BOOLEAN NOT NULL DEFAULT FALSE,
            installment_count INTEGER,
            installment_frequency installmentfrequency,
            cash_price BIGINT,
            down_payment BIGINT,
            interest_percent INTEGER,
            affects_balance BOOLEAN NOT NULL DEFAULT FALSE,
            created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
            CONSTRAINT ck_debts_total_amount_positive CHECK (total_amount > 0),
            CONSTRAINT ck_debts_paid_amount_non_negative CHECK (paid_amount >= 0),
            CONSTRAINT ck_debts_paid_not_exceed_total CHECK (paid_amount <= total_amount),
            CONSTRAINT ck_debts_cash_price_positive CHECK (cash_price IS NULL OR cash_price > 0),
            CONSTRAINT ck_debts_down_payment_non_negative CHECK (down_payment IS NULL OR down_payment >= 0),
            CONSTRAINT ck_debts_down_payment_less_than_cash CHECK (down_payment IS NULL OR cash_price IS NULL OR down_payment < cash_price),
            CONSTRAINT ck_debts_interest_percent_non_negative CHECK (interest_percent IS NULL OR interest_percent >= 0),
            CONSTRAINT ck_debts_installment_count_positive CHECK (installment_count IS NULL OR installment_count > 0),
            CONSTRAINT ck_debts_start_date_min_2020_01_01 CHECK (start_date >= '2020-01-01'),
            CONSTRAINT ck_debts_due_date_after_start CHECK (due_date IS NULL OR due_date >= start_date)
        )
    """)
    op.create_index('ix_debts_owner_id', 'debts', ['owner_id'])
    op.create_index('ix_debts_owner_status', 'debts', ['owner_id', 'status'])
    op.create_index('ix_debts_owner_type', 'debts', ['owner_id', 'debt_type'])

    # Create debt_payments table
    op.execute("""
        CREATE TABLE debt_payments (
            id SERIAL PRIMARY KEY,
            owner_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            debt_id INTEGER NOT NULL REFERENCES debts(id) ON DELETE CASCADE,
            amount BIGINT NOT NULL,
            payment_type debtpaymenttype NOT NULL,
            status debtpaymentstatus NOT NULL DEFAULT 'PENDING',
            due_date DATE NOT NULL,
            paid_date DATE,
            note VARCHAR(200),
            expense_id INTEGER REFERENCES expenses(id) ON DELETE SET NULL,
            created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
            CONSTRAINT ck_debt_payments_amount_positive CHECK (amount > 0)
        )
    """)
    op.create_index('ix_debt_payments_owner_id', 'debt_payments', ['owner_id'])
    op.create_index('ix_debt_payments_debt_id', 'debt_payments', ['debt_id'])
    op.create_index('ix_debt_payments_debt_due_date', 'debt_payments', ['debt_id', 'due_date'])
    op.create_index('ix_debt_payments_owner_due_date', 'debt_payments', ['owner_id', 'due_date'])

    # Add total_debts_created column to users
    op.add_column('users', sa.Column('total_debts_created', sa.Integer(), nullable=False, server_default='0'))


def downgrade() -> None:
    """Downgrade schema."""
    # Remove total_debts_created column
    op.drop_column('users', 'total_debts_created')

    # Drop debt_payments table
    op.execute("DROP TABLE IF EXISTS debt_payments")

    # Drop debts table
    op.execute("DROP TABLE IF EXISTS debts")
