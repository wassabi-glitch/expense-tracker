"""add_realistic_wallet_types_and_limits

Revision ID: 4a4137a6643b
Revises: 442c5a94ed01
Create Date: 2026-04-14 21:21:06.346848

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '4a4137a6643b'
down_revision: Union[str, Sequence[str], None] = '442c5a94ed01'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # 1. Create Enums explicitly for PostgreSQL
    wallet_type_enum = sa.Enum('CASH', 'DEBIT', 'CREDIT', 'PRELOADED', name='wallettype')
    accounting_type_enum = sa.Enum('ASSET', 'LIABILITY', name='accountingtype')
    wallet_type_enum.create(op.get_bind())
    accounting_type_enum.create(op.get_bind())

    # 2. Add columns as nullable first to allow backfilling
    op.add_column('wallets', sa.Column('wallet_type', wallet_type_enum, nullable=True))
    op.add_column('wallets', sa.Column('accounting_type', accounting_type_enum, nullable=True))
    op.add_column('wallets', sa.Column('overdraft_limit', sa.BigInteger(), nullable=True, server_default='0'))
    op.add_column('wallets', sa.Column('has_overdraft', sa.Boolean(), nullable=True, server_default='false'))
    op.add_column('wallets', sa.Column('credit_limit', sa.BigInteger(), nullable=True, server_default='0'))
    op.add_column('wallets', sa.Column('allow_overlimit', sa.Boolean(), nullable=True, server_default='false'))
    op.add_column('wallets', sa.Column('is_active', sa.Boolean(), nullable=True, server_default='true'))

    # 3. Backfill existing data
    op.execute("UPDATE wallets SET wallet_type = 'DEBIT' WHERE wallet_type IS NULL")
    op.execute("UPDATE wallets SET accounting_type = 'ASSET' WHERE accounting_type IS NULL")
    op.execute("UPDATE wallets SET has_overdraft = false WHERE has_overdraft IS NULL")
    op.execute("UPDATE wallets SET credit_limit = 0 WHERE credit_limit IS NULL")
    op.execute("UPDATE wallets SET allow_overlimit = false WHERE allow_overlimit IS NULL")
    op.execute("UPDATE wallets SET is_active = true WHERE is_active IS NULL")

    # 4. Now set columns to NOT NULL
    op.alter_column('wallets', 'wallet_type', nullable=False)
    op.alter_column('wallets', 'accounting_type', nullable=False)
    op.alter_column('wallets', 'has_overdraft', nullable=False)
    op.alter_column('wallets', 'credit_limit', nullable=False)
    op.alter_column('wallets', 'allow_overlimit', nullable=False)
    op.alter_column('wallets', 'is_active', nullable=False)

    # 5. Drop the legacy non-negative balance constraint
    op.drop_constraint('ck_wallets_current_balance_non_negative', 'wallets', type_='check')


def downgrade() -> None:
    """Downgrade schema."""
    # Re-add the constraint (Simplified, might fail if negative balances exist)
    op.create_check_constraint('ck_wallets_current_balance_non_negative', 'wallets', 'current_balance >= 0')
    
    op.drop_column('wallets', 'is_active')
    op.drop_column('wallets', 'allow_overlimit')
    op.drop_column('wallets', 'credit_limit')
    op.drop_column('wallets', 'has_overdraft')
    op.drop_column('wallets', 'overdraft_limit')
    op.drop_column('wallets', 'accounting_type')
    op.drop_column('wallets', 'wallet_type')

    # Drop Enums
    sa.Enum(name='wallettype').drop(op.get_bind())
    sa.Enum(name='accountingtype').drop(op.get_bind())
