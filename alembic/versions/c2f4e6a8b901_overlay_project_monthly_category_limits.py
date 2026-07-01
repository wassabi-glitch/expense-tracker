"""overlay project monthly category limits

Revision ID: c2f4e6a8b901
Revises: b6c7d8e9f0a1
Create Date: 2026-07-01 10:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = "c2f4e6a8b901"
down_revision: Union[str, Sequence[str], None] = "b6c7d8e9f0a1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    expense_category_enum = postgresql.ENUM(name="expensecategory", create_type=False)
    op.create_table(
        "project_category_monthly_limits",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("project_id", sa.Integer(), nullable=False),
        sa.Column("category", expense_category_enum, nullable=False),
        sa.Column("budget_year", sa.Integer(), nullable=False),
        sa.Column("budget_month", sa.Integer(), nullable=False),
        sa.Column("limit_amount", sa.BigInteger(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("budget_month >= 1 AND budget_month <= 12", name="ck_project_category_monthly_limits_month"),
        sa.CheckConstraint("budget_year >= 2020", name="ck_project_category_monthly_limits_year"),
        sa.CheckConstraint("limit_amount > 0", name="ck_project_category_monthly_limits_amount_positive"),
        sa.CheckConstraint("limit_amount <= 999999999999", name="ck_project_category_monthly_limits_amount_max"),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "project_id",
            "category",
            "budget_year",
            "budget_month",
            name="uq_project_category_monthly_limits_project_category_month",
        ),
    )
    op.create_index(op.f("ix_project_category_monthly_limits_id"), "project_category_monthly_limits", ["id"], unique=False)
    op.create_index(
        op.f("ix_project_category_monthly_limits_project_id"),
        "project_category_monthly_limits",
        ["project_id"],
        unique=False,
    )
    op.create_index(
        "ix_project_category_monthly_limits_month",
        "project_category_monthly_limits",
        ["budget_year", "budget_month", "category"],
        unique=False,
    )

    op.execute(
        """
        INSERT INTO project_category_monthly_limits (
            project_id,
            category,
            budget_year,
            budget_month,
            limit_amount,
            created_at,
            updated_at
        )
        SELECT
            pcl.project_id,
            pcl.category,
            EXTRACT(YEAR FROM p.start_date)::integer AS budget_year,
            EXTRACT(MONTH FROM p.start_date)::integer AS budget_month,
            pcl.limit_amount,
            now(),
            now()
        FROM project_category_limits pcl
        JOIN projects p ON p.id = pcl.project_id
        WHERE p.is_isolated = false
        ON CONFLICT (project_id, category, budget_year, budget_month)
        DO UPDATE SET
            limit_amount = EXCLUDED.limit_amount,
            updated_at = now()
        """
    )
    op.execute(
        """
        DELETE FROM project_category_limits pcl
        USING projects p
        WHERE p.id = pcl.project_id
          AND p.is_isolated = false
        """
    )


def downgrade() -> None:
    op.execute(
        """
        INSERT INTO project_category_limits (project_id, category, limit_amount)
        SELECT project_id, category, SUM(limit_amount)::bigint AS limit_amount
        FROM project_category_monthly_limits
        GROUP BY project_id, category
        ON CONFLICT (project_id, category)
        DO UPDATE SET limit_amount = EXCLUDED.limit_amount
        """
    )
    op.drop_index("ix_project_category_monthly_limits_month", table_name="project_category_monthly_limits")
    op.drop_index(op.f("ix_project_category_monthly_limits_project_id"), table_name="project_category_monthly_limits")
    op.drop_index(op.f("ix_project_category_monthly_limits_id"), table_name="project_category_monthly_limits")
    op.drop_table("project_category_monthly_limits")
