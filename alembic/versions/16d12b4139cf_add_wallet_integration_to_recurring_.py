"""add_wallet_integration_to_recurring_expenses

Revision ID: 16d12b4139cf
Revises: 7793d5500b70
Create Date: 2026-04-27 12:44:56.175535

Adds wallet_id, status (enum), cycle_behavior (enum), retry_count,
and last_retry_at to recurring_expenses. Replaces the old boolean
is_active column with the richer RecurringStatus enum, migrating
existing data: is_active=True → ACTIVE, is_active=False → DISABLED.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '16d12b4139cf'
down_revision: Union[str, Sequence[str], None] = '7793d5500b70'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# ── Enum definitions for PostgreSQL ──────────────────────────────────
recurringstatus_enum = sa.Enum(
    'ACTIVE', 'DISABLED', 'RETRYING', 'PAUSED',
    name='recurringstatus',
)
cyclebehavior_enum = sa.Enum(
    'FIXED', 'FLEXIBLE',
    name='cyclebehavior',
)


def upgrade() -> None:
    """Upgrade schema."""

    # 1. Create the PostgreSQL enum types first (they live independently of tables)
    recurringstatus_enum.create(op.get_bind(), checkfirst=True)
    cyclebehavior_enum.create(op.get_bind(), checkfirst=True)

    # 2. Add wallet_id (FK to wallets, nullable because old templates have none)
    op.add_column('recurring_expenses', sa.Column(
        'wallet_id', sa.Integer(), nullable=True,
    ))
    op.create_index(
        op.f('ix_recurring_expenses_wallet_id'),
        'recurring_expenses', ['wallet_id'], unique=False,
    )
    op.create_foreign_key(
        'fk_recurring_expenses_wallet_id',
        'recurring_expenses', 'wallets',
        ['wallet_id'], ['id'],
        ondelete='SET NULL',
    )

    # 3. Add status as NULLABLE first (can't add NOT NULL to a table with rows)
    op.add_column('recurring_expenses', sa.Column(
        'status', recurringstatus_enum, nullable=True,
    ))

    # 4. DATA MIGRATION: Convert is_active boolean → status enum
    #    is_active=True  → 'ACTIVE'
    #    is_active=False → 'DISABLED'
    op.execute("""
        UPDATE recurring_expenses
        SET status = CASE
            WHEN is_active = TRUE  THEN 'ACTIVE'::recurringstatus
            WHEN is_active = FALSE THEN 'DISABLED'::recurringstatus
            ELSE 'ACTIVE'::recurringstatus
        END
    """)

    # 5. Now that all rows have a status value, make it NOT NULL
    op.alter_column('recurring_expenses', 'status', nullable=False)

    # 6. Drop the old is_active column (replaced by status)
    op.drop_column('recurring_expenses', 'is_active')

    # 7. Add remaining new columns
    op.add_column('recurring_expenses', sa.Column(
        'cycle_behavior', cyclebehavior_enum,
        nullable=False, server_default='FIXED',
    ))
    op.add_column('recurring_expenses', sa.Column(
        'retry_count', sa.Integer(),
        nullable=False, server_default='0',
    ))
    op.add_column('recurring_expenses', sa.Column(
        'last_retry_at', sa.DateTime(timezone=True), nullable=True,
    ))

    # 8. Add original_due_day and backfill it from next_due_date
    op.add_column('recurring_expenses', sa.Column(
        'original_due_day', sa.Integer(), nullable=True,
    ))
    op.execute("UPDATE recurring_expenses SET original_due_day = EXTRACT(DAY FROM next_due_date)")


def downgrade() -> None:
    """Downgrade schema: restore is_active boolean, remove new columns."""

    # 1. Re-add is_active as nullable first
    op.add_column('recurring_expenses', sa.Column(
        'is_active', sa.BOOLEAN(), nullable=True,
    ))

    # 2. Reverse data migration: status enum → is_active boolean
    op.execute("""
        UPDATE recurring_expenses
        SET is_active = CASE
            WHEN status = 'DISABLED' THEN FALSE
            ELSE TRUE
        END
    """)

    # 3. Make is_active NOT NULL
    op.alter_column('recurring_expenses', 'is_active', nullable=False)

    # 4. Drop new columns
    op.drop_column('recurring_expenses', 'original_due_day')
    op.drop_column('recurring_expenses', 'last_retry_at')
    op.drop_column('recurring_expenses', 'retry_count')
    op.drop_column('recurring_expenses', 'cycle_behavior')
    op.drop_column('recurring_expenses', 'status')

    # 5. Drop wallet FK and column
    op.drop_constraint('fk_recurring_expenses_wallet_id', 'recurring_expenses', type_='foreignkey')
    op.drop_index(op.f('ix_recurring_expenses_wallet_id'), table_name='recurring_expenses')
    op.drop_column('recurring_expenses', 'wallet_id')

    # 6. Drop the PostgreSQL enum types
    cyclebehavior_enum.drop(op.get_bind(), checkfirst=True)
    recurringstatus_enum.drop(op.get_bind(), checkfirst=True)
