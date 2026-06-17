"""simplify_wallet_status_to_is_active

Revision ID: d8c0b7a1e4f2
Revises: 1dddd378d1d5
Create Date: 2026-04-22 14:10:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'd8c0b7a1e4f2'
down_revision: Union[str, Sequence[str], None] = '1dddd378d1d5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        UPDATE wallets
        SET is_active = CASE
            WHEN status = 'ARCHIVED' THEN FALSE
            ELSE TRUE
        END
        WHERE status IS NOT NULL
        """
    )
    op.drop_index(op.f('ix_wallets_status'), table_name='wallets')
    op.drop_column('wallets', 'status')
    postgresql.ENUM(name='walletstatus').drop(op.get_bind(), checkfirst=True)


def downgrade() -> None:
    wallet_status = postgresql.ENUM('ACTIVE', 'FROZEN', 'BLOCKED', 'EXPIRED', 'ARCHIVED', name='walletstatus')
    wallet_status.create(op.get_bind(), checkfirst=True)
    op.add_column(
        'wallets',
        sa.Column(
            'status',
            sa.Enum('ACTIVE', 'FROZEN', 'BLOCKED', 'EXPIRED', 'ARCHIVED', name='walletstatus'),
            nullable=True,
        ),
    )
    op.create_index(op.f('ix_wallets_status'), 'wallets', ['status'], unique=False)
    op.execute("UPDATE wallets SET status = 'ACTIVE' WHERE is_active = TRUE")
    op.execute("UPDATE wallets SET status = 'ARCHIVED' WHERE is_active = FALSE")
    op.alter_column('wallets', 'status', nullable=False)
