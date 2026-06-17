"""add financial event void status

Revision ID: 4a6c7285ade1
Revises: c6f9a2e8b431
Create Date: 2026-05-20 18:26:28.453400

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = '4a6c7285ade1'
down_revision: Union[str, Sequence[str], None] = 'c6f9a2e8b431'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    event_status = postgresql.ENUM('POSTED', 'VOIDED', 'REVERSAL', name='financialeventstatus')
    event_status.create(op.get_bind(), checkfirst=True)

    op.add_column('financial_events', sa.Column('status', event_status, server_default='POSTED', nullable=False))
    op.add_column('financial_events', sa.Column('void_reversal_event_id', sa.Integer(), nullable=True))
    op.add_column('financial_events', sa.Column('reverses_event_id', sa.Integer(), nullable=True))
    op.add_column('financial_events', sa.Column('voided_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('financial_events', sa.Column('void_reason', sa.String(length=500), nullable=True))
    op.create_index(op.f('ix_financial_events_reverses_event_id'), 'financial_events', ['reverses_event_id'], unique=False)
    op.create_index(op.f('ix_financial_events_status'), 'financial_events', ['status'], unique=False)
    op.create_index(op.f('ix_financial_events_void_reversal_event_id'), 'financial_events', ['void_reversal_event_id'], unique=False)
    op.create_foreign_key('fk_financial_events_reverses_event_id', 'financial_events', 'financial_events', ['reverses_event_id'], ['id'], ondelete='SET NULL')
    op.create_foreign_key('fk_financial_events_void_reversal_event_id', 'financial_events', 'financial_events', ['void_reversal_event_id'], ['id'], ondelete='SET NULL')


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint('fk_financial_events_void_reversal_event_id', 'financial_events', type_='foreignkey')
    op.drop_constraint('fk_financial_events_reverses_event_id', 'financial_events', type_='foreignkey')
    op.drop_index(op.f('ix_financial_events_void_reversal_event_id'), table_name='financial_events')
    op.drop_index(op.f('ix_financial_events_status'), table_name='financial_events')
    op.drop_index(op.f('ix_financial_events_reverses_event_id'), table_name='financial_events')
    op.drop_column('financial_events', 'void_reason')
    op.drop_column('financial_events', 'voided_at')
    op.drop_column('financial_events', 'reverses_event_id')
    op.drop_column('financial_events', 'void_reversal_event_id')
    op.drop_column('financial_events', 'status')
    postgresql.ENUM(name='financialeventstatus').drop(op.get_bind(), checkfirst=True)
