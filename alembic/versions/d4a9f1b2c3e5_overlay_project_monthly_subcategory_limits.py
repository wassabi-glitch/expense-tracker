"""overlay project monthly subcategory limits

Revision ID: d4a9f1b2c3e5
Revises: c2f4e6a8b901
Create Date: 2026-07-01 12:15:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = "d4a9f1b2c3e5"
down_revision: Union[str, Sequence[str], None] = "c2f4e6a8b901"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    expense_category_enum = postgresql.ENUM(name="expensecategory", create_type=False)
    op.create_table(
        "project_subcategory_monthly_limits",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("project_id", sa.Integer(), nullable=False),
        sa.Column("user_subcategory_id", sa.Integer(), nullable=False),
        sa.Column("category", expense_category_enum, nullable=False),
        sa.Column("budget_year", sa.Integer(), nullable=False),
        sa.Column("budget_month", sa.Integer(), nullable=False),
        sa.Column("limit_amount", sa.BigInteger(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("budget_month >= 1 AND budget_month <= 12", name="ck_project_subcategory_monthly_limits_month"),
        sa.CheckConstraint("budget_year >= 2020", name="ck_project_subcategory_monthly_limits_year"),
        sa.CheckConstraint("limit_amount > 0", name="ck_project_subcategory_monthly_limits_amount_positive"),
        sa.CheckConstraint("limit_amount <= 999999999999", name="ck_project_subcategory_monthly_limits_amount_max"),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_subcategory_id"], ["user_subcategories.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "project_id",
            "user_subcategory_id",
            "budget_year",
            "budget_month",
            name="uq_project_subcategory_monthly_limits_project_subcategory_month",
        ),
    )
    op.create_index(op.f("ix_project_subcategory_monthly_limits_id"), "project_subcategory_monthly_limits", ["id"], unique=False)
    op.create_index(
        op.f("ix_project_subcategory_monthly_limits_project_id"),
        "project_subcategory_monthly_limits",
        ["project_id"],
        unique=False,
    )
    op.create_index(
        "ix_project_subcategory_monthly_limits_month",
        "project_subcategory_monthly_limits",
        ["budget_year", "budget_month", "category"],
        unique=False,
    )
    op.create_index(
        "ix_project_subcategory_monthly_limits_subcategory",
        "project_subcategory_monthly_limits",
        ["user_subcategory_id"],
        unique=False,
    )

    op.execute(
        """
        INSERT INTO user_subcategories (
            owner_id,
            category,
            name,
            is_active,
            is_deleted,
            created_at
        )
        SELECT
            p.owner_id,
            ps.category,
            ps.name,
            bool_or(ps.is_active),
            false,
            min(ps.created_at)
        FROM project_subcategories ps
        JOIN projects p ON p.id = ps.project_id
        WHERE p.is_isolated = false
        GROUP BY p.owner_id, ps.category, ps.name
        ON CONFLICT (owner_id, category, name)
        DO UPDATE SET
            is_active = user_subcategories.is_active OR EXCLUDED.is_active,
            is_deleted = false
        """
    )

    op.execute(
        """
        UPDATE entity_ledger el
        SET subcategory_id = us.id
        FROM project_subcategories ps
        JOIN projects p ON p.id = ps.project_id
        JOIN user_subcategories us
          ON us.owner_id = p.owner_id
         AND us.category = ps.category
         AND us.name = ps.name
        WHERE el.project_subcategory_id = ps.id
          AND p.is_isolated = false
          AND el.subcategory_id IS NULL
        """
    )

    op.execute(
        """
        INSERT INTO project_subcategory_monthly_limits (
            project_id,
            user_subcategory_id,
            category,
            budget_year,
            budget_month,
            limit_amount,
            created_at,
            updated_at
        )
        SELECT
            ps.project_id,
            us.id AS user_subcategory_id,
            ps.category,
            EXTRACT(YEAR FROM p.start_date)::integer AS budget_year,
            EXTRACT(MONTH FROM p.start_date)::integer AS budget_month,
            ps.limit_amount,
            now(),
            now()
        FROM project_subcategories ps
        JOIN projects p ON p.id = ps.project_id
        JOIN user_subcategories us
          ON us.owner_id = p.owner_id
         AND us.category = ps.category
         AND us.name = ps.name
        JOIN budgets b
          ON b.owner_id = p.owner_id
         AND b.category = ps.category
         AND b.budget_year = EXTRACT(YEAR FROM p.start_date)::integer
         AND b.budget_month = EXTRACT(MONTH FROM p.start_date)::integer
        JOIN budget_subcategory_limits bsl
          ON bsl.owner_id = p.owner_id
         AND bsl.budget_id = b.id
         AND bsl.subcategory_id = us.id
        WHERE p.is_isolated = false
          AND ps.limit_amount IS NOT NULL
        ON CONFLICT (project_id, user_subcategory_id, budget_year, budget_month)
        DO UPDATE SET
            limit_amount = EXCLUDED.limit_amount,
            updated_at = now()
        """
    )


def downgrade() -> None:
    op.drop_index("ix_project_subcategory_monthly_limits_subcategory", table_name="project_subcategory_monthly_limits")
    op.drop_index("ix_project_subcategory_monthly_limits_month", table_name="project_subcategory_monthly_limits")
    op.drop_index(op.f("ix_project_subcategory_monthly_limits_project_id"), table_name="project_subcategory_monthly_limits")
    op.drop_index(op.f("ix_project_subcategory_monthly_limits_id"), table_name="project_subcategory_monthly_limits")
    op.drop_table("project_subcategory_monthly_limits")
