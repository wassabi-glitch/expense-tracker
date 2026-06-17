"""add budget subcategory limits

Revision ID: 6b7c8d9e0f12
Revises: 1f7c2d9e4a60
Create Date: 2026-06-14 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "6b7c8d9e0f12"
down_revision: Union[str, Sequence[str], None] = "1f7c2d9e4a60"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "budget_subcategory_limits",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("owner_id", sa.Integer(), nullable=False),
        sa.Column("budget_id", sa.Integer(), nullable=False),
        sa.Column("subcategory_id", sa.Integer(), nullable=False),
        sa.Column("monthly_limit", sa.BigInteger(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("monthly_limit > 0", name="ck_budget_subcategory_limits_monthly_limit_positive"),
        sa.CheckConstraint("monthly_limit <= 999999999999", name="ck_budget_subcategory_limits_monthly_limit_max"),
        sa.ForeignKeyConstraint(["budget_id"], ["budgets.id"], name="fk_budget_subcategory_limits_budget_id_budgets", ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"], name="fk_budget_subcategory_limits_owner_id_users", ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["subcategory_id"],
            ["user_subcategories.id"],
            name="fk_budget_subcategory_limits_subcategory_id_user_subcategories",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("budget_id", "subcategory_id", name="uq_budget_subcategory_limits_budget_subcategory"),
    )
    op.create_index(op.f("ix_budget_subcategory_limits_id"), "budget_subcategory_limits", ["id"], unique=False)
    op.create_index("ix_budget_subcategory_limits_budget", "budget_subcategory_limits", ["budget_id"], unique=False)
    op.create_index("ix_budget_subcategory_limits_subcategory", "budget_subcategory_limits", ["subcategory_id"], unique=False)
    op.create_index(op.f("ix_budget_subcategory_limits_owner_id"), "budget_subcategory_limits", ["owner_id"], unique=False)

    op.execute(
        """
        INSERT INTO budget_subcategory_limits (owner_id, budget_id, subcategory_id, monthly_limit)
        SELECT us.owner_id, b.id, us.id, us.monthly_limit
        FROM user_subcategories us
        JOIN budgets b
          ON b.owner_id = us.owner_id
         AND b.category = us.category
        WHERE us.monthly_limit IS NOT NULL
        """
    )
    op.drop_column("user_subcategories", "monthly_limit")


def downgrade() -> None:
    op.add_column("user_subcategories", sa.Column("monthly_limit", sa.BigInteger(), nullable=True))
    op.execute(
        """
        UPDATE user_subcategories us
        SET monthly_limit = latest.monthly_limit
        FROM (
            SELECT DISTINCT ON (bsl.subcategory_id)
                bsl.subcategory_id,
                bsl.monthly_limit
            FROM budget_subcategory_limits bsl
            JOIN budgets b ON b.id = bsl.budget_id
            ORDER BY bsl.subcategory_id, b.budget_year DESC, b.budget_month DESC, bsl.id DESC
        ) latest
        WHERE latest.subcategory_id = us.id
        """
    )
    op.drop_index(op.f("ix_budget_subcategory_limits_owner_id"), table_name="budget_subcategory_limits")
    op.drop_index("ix_budget_subcategory_limits_subcategory", table_name="budget_subcategory_limits")
    op.drop_index("ix_budget_subcategory_limits_budget", table_name="budget_subcategory_limits")
    op.drop_index(op.f("ix_budget_subcategory_limits_id"), table_name="budget_subcategory_limits")
    op.drop_table("budget_subcategory_limits")
