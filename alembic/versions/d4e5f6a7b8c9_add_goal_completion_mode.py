"""add goal completion mode

Revision ID: d4e5f6a7b8c9
Revises: c3d4e5f6a7b8
Create Date: 2026-05-27 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "d4e5f6a7b8c9"
down_revision: Union[str, Sequence[str], None] = "c3d4e5f6a7b8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


COMPLETION_MODES = (
    "GOAL_FUNDED",
    "ACHIEVED_OUTSIDE_RESERVED_FUNDS",
)


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        completion_mode = postgresql.ENUM(*COMPLETION_MODES, name="goalcompletionmode")
        completion_mode.create(bind, checkfirst=True)
        column_type = postgresql.ENUM(*COMPLETION_MODES, name="goalcompletionmode", create_type=False)
    else:
        column_type = sa.Enum(*COMPLETION_MODES, name="goalcompletionmode")

    op.add_column("goals", sa.Column("completion_mode", column_type, nullable=True))

    if bind.dialect.name == "postgresql":
        op.execute(
            """
            UPDATE goals
            SET completion_mode = 'GOAL_FUNDED'
            WHERE status::text = 'COMPLETED'
              AND linked_expense_event_id IS NOT NULL
            """
        )
    else:
        op.execute(
            """
            UPDATE goals
            SET completion_mode = 'GOAL_FUNDED'
            WHERE status = 'COMPLETED'
              AND linked_expense_event_id IS NOT NULL
            """
        )


def downgrade() -> None:
    op.drop_column("goals", "completion_mode")

    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.execute("DROP TYPE IF EXISTS goalcompletionmode")
