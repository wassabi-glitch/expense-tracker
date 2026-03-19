"""add notifications table

Revision ID: a1b2c3d4e5f6
Revises: f3a0a1e2b4c5
Create Date: 2026-03-18 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, Sequence[str], None] = 'f3a0a1e2b4c5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table('notifications',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('owner_id', sa.Integer(), nullable=False),
    sa.Column('type', sa.String(length=50), nullable=False),
    sa.Column('title', sa.String(length=100), nullable=False),
    sa.Column('message', sa.String(length=500), nullable=False),
    sa.Column('is_read', sa.Boolean(), nullable=False, server_default='false'),
    sa.Column('priority', sa.String(length=20), nullable=False, server_default='info'),
    sa.Column('extra_data', sa.JSON(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['owner_id'], ['users.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_notifications_owner_id', 'notifications', ['owner_id'], unique=False)
    op.create_index('ix_notifications_owner_is_read', 'notifications', ['owner_id', 'is_read'], unique=False)
    op.create_index('ix_notifications_owner_created_at', 'notifications', ['owner_id', 'created_at'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index('ix_notifications_owner_created_at', table_name='notifications')
    op.drop_index('ix_notifications_owner_is_read', table_name='notifications')
    op.drop_index('ix_notifications_owner_id', table_name='notifications')
    op.drop_table('notifications')
