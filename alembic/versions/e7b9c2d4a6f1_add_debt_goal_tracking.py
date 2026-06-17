"""add debt goal tracking

Revision ID: e7b9c2d4a6f1
Revises: a8d9c2e7f104
Create Date: 2026-06-04 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "e7b9c2d4a6f1"
down_revision: Union[str, Sequence[str], None] = "a8d9c2e7f104"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


TRACKING_MODES = (
    "FULL_REMAINING_DEBT",
    "FIXED_DEBT_AMOUNT",
)


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        tracking_mode = postgresql.ENUM(*TRACKING_MODES, name="debtgoaltrackingmode")
        tracking_mode.create(bind, checkfirst=True)
        tracking_type = postgresql.ENUM(*TRACKING_MODES, name="debtgoaltrackingmode", create_type=False)
    else:
        tracking_type = sa.Enum(*TRACKING_MODES, name="debtgoaltrackingmode")

    op.add_column("goals", sa.Column("debt_goal_tracking_mode", tracking_type, nullable=True))
    op.add_column("goals", sa.Column("linked_debt_transaction_id", sa.Integer(), nullable=True))
    op.create_index(
        op.f("ix_goals_linked_debt_transaction_id"),
        "goals",
        ["linked_debt_transaction_id"],
        unique=False,
    )
    op.create_foreign_key(
        "fk_goals_linked_debt_transaction_id",
        "goals",
        "debt_transactions",
        ["linked_debt_transaction_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(
        "ux_goals_one_active_pay_obligation_per_debt",
        "goals",
        ["owner_id", "linked_debt_id"],
        unique=True,
        postgresql_where=sa.text("intent = 'PAY_OBLIGATION' AND status = 'ACTIVE' AND linked_debt_id IS NOT NULL"),
        sqlite_where=sa.text("intent = 'PAY_OBLIGATION' AND status = 'ACTIVE' AND linked_debt_id IS NOT NULL"),
    )


def downgrade() -> None:
    op.drop_index("ux_goals_one_active_pay_obligation_per_debt", table_name="goals")
    op.drop_constraint("fk_goals_linked_debt_transaction_id", "goals", type_="foreignkey")
    op.drop_index(op.f("ix_goals_linked_debt_transaction_id"), table_name="goals")
    op.drop_column("goals", "linked_debt_transaction_id")
    op.drop_column("goals", "debt_goal_tracking_mode")

    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.execute("DROP TYPE IF EXISTS debtgoaltrackingmode")
