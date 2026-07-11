"""add_receipt_and_write_off_reversal_support

Revision ID: 602f3bc5ab4c
Revises: 2fe184d64444
Create Date: 2026-07-11 11:26:27.366072

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '602f3bc5ab4c'
down_revision: Union[str, Sequence[str], None] = '2fe184d64444'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Ticket 7 & 8: Add receipt reversal columns and write-off reversal table."""
    # Ticket 7: Receipt reversal — add reversed_at / reversal_note to realizations.
    op.add_column(
        'expected_inflow_realizations',
        sa.Column('reversed_at', sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        'expected_inflow_realizations',
        sa.Column('reversal_note', sa.String(length=200), nullable=True),
    )

    # Ticket 8: Write-off reversal — dedicated append-only reversal table.
    op.create_table(
        'expected_inflow_write_off_reversals',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('owner_id', sa.Integer(), nullable=False),
        sa.Column('write_off_id', sa.Integer(), nullable=False),
        sa.Column('promise_id', sa.Integer(), nullable=False),
        sa.Column('note', sa.String(length=200), nullable=True),
        sa.Column(
            'created_at',
            sa.DateTime(timezone=True),
            server_default=sa.text('now()'),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ['owner_id'], ['users.id'], ondelete='CASCADE',
        ),
        sa.ForeignKeyConstraint(
            ['promise_id'],
            ['expected_inflow_promises.id'],
            ondelete='CASCADE',
        ),
        sa.ForeignKeyConstraint(
            ['write_off_id'],
            ['expected_inflow_write_offs.id'],
            ondelete='CASCADE',
        ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint(
            'write_off_id',
            name='uq_expected_inflow_write_off_reversals_write_off_id',
        ),
    )
    op.create_index(
        op.f('ix_expected_inflow_write_off_reversals_id'),
        'expected_inflow_write_off_reversals',
        ['id'],
        unique=False,
    )
    op.create_index(
        op.f('ix_expected_inflow_write_off_reversals_owner_id'),
        'expected_inflow_write_off_reversals',
        ['owner_id'],
        unique=False,
    )
    op.create_index(
        op.f('ix_expected_inflow_write_off_reversals_promise_id'),
        'expected_inflow_write_off_reversals',
        ['promise_id'],
        unique=False,
    )
    op.create_index(
        op.f('ix_expected_inflow_write_off_reversals_write_off_id'),
        'expected_inflow_write_off_reversals',
        ['write_off_id'],
        unique=False,
    )

    # Backfill reversal records for write-offs that were already reversed
    # before the append-only reversal table existed.
    op.execute("""
        INSERT INTO expected_inflow_write_off_reversals
            (owner_id, write_off_id, promise_id, note, created_at)
        SELECT
            wo.owner_id,
            wo.id,
            wo.promise_id,
            wo.reversal_note,
            wo.reversed_at
        FROM expected_inflow_write_offs wo
        WHERE wo.reversed_at IS NOT NULL
          AND NOT EXISTS (
              SELECT 1 FROM expected_inflow_write_off_reversals r
              WHERE r.write_off_id = wo.id
          )
    """)


def downgrade() -> None:
    """Reverse Ticket 7 & 8 schema changes."""
    op.drop_index(
        op.f('ix_expected_inflow_write_off_reversals_write_off_id'),
        table_name='expected_inflow_write_off_reversals',
    )
    op.drop_index(
        op.f('ix_expected_inflow_write_off_reversals_promise_id'),
        table_name='expected_inflow_write_off_reversals',
    )
    op.drop_index(
        op.f('ix_expected_inflow_write_off_reversals_owner_id'),
        table_name='expected_inflow_write_off_reversals',
    )
    op.drop_index(
        op.f('ix_expected_inflow_write_off_reversals_id'),
        table_name='expected_inflow_write_off_reversals',
    )
    op.drop_table('expected_inflow_write_off_reversals')
    op.drop_column('expected_inflow_realizations', 'reversal_note')
    op.drop_column('expected_inflow_realizations', 'reversed_at')
