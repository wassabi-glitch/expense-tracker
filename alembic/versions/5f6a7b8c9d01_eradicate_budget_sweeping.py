"""eradicate_budget_sweeping

Revision ID: 5f6a7b8c9d01
Revises: 4b8f0d6e2a91
Create Date: 2026-06-19 16:45:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = "5f6a7b8c9d01"
down_revision: Union[str, Sequence[str], None] = "4b8f0d6e2a91"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


OLD_BUDGET_LEDGER_TYPE = postgresql.ENUM(
    "ROLLOVER",
    "SWEEP",
    "CAP_TRIM",
    name="budgetledgertype",
)


def upgrade() -> None:
    bind = op.get_bind()

    if bind.dialect.name == "postgresql":
        op.alter_column(
            "budget_ledger",
            "entry_type",
            existing_type=OLD_BUDGET_LEDGER_TYPE,
            type_=sa.String(length=20),
            existing_nullable=False,
            postgresql_using="entry_type::text",
        )
        op.execute("DROP TYPE IF EXISTS budgetledgertype")

    op.drop_column("budgets", "sweep_target_goal_id")


def downgrade() -> None:
    bind = op.get_bind()

    op.add_column("budgets", sa.Column("sweep_target_goal_id", sa.Integer(), nullable=True))
    op.create_foreign_key(
        None,
        "budgets",
        "goals",
        ["sweep_target_goal_id"],
        ["id"],
        ondelete="SET NULL",
    )

    if bind.dialect.name == "postgresql":
        OLD_BUDGET_LEDGER_TYPE.create(bind, checkfirst=True)
        op.alter_column(
            "budget_ledger",
            "entry_type",
            existing_type=sa.String(length=20),
            type_=OLD_BUDGET_LEDGER_TYPE,
            existing_nullable=False,
            postgresql_using="entry_type::budgetledgertype",
        )
