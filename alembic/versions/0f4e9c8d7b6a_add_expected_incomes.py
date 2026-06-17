"""add expected incomes

Revision ID: 0f4e9c8d7b6a
Revises: f4c7b9e2a130
Create Date: 2026-06-08 22:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "0f4e9c8d7b6a"
down_revision: Union[str, Sequence[str], None] = "f4c7b9e2a130"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


expected_income_status = postgresql.ENUM(
    "EXPECTED",
    "RECEIVED",
    "MISSED",
    "CANCELLED",
    name="expectedincomestatus",
    create_type=False,
)


def upgrade() -> None:
    expected_income_status.create(op.get_bind(), checkfirst=True)
    op.create_table(
        "expected_incomes",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("owner_id", sa.Integer(), nullable=False),
        sa.Column("source_id", sa.Integer(), nullable=True),
        sa.Column("amount", sa.BigInteger(), nullable=False),
        sa.Column("due_date", sa.Date(), nullable=False),
        sa.Column("budget_year", sa.Integer(), nullable=False),
        sa.Column("budget_month", sa.Integer(), nullable=False),
        sa.Column("status", expected_income_status, nullable=False),
        sa.Column("note", sa.String(length=200), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("amount > 0", name="ck_expected_incomes_amount_positive"),
        sa.CheckConstraint("amount <= 999999999999", name="ck_expected_incomes_amount_limit"),
        sa.CheckConstraint("due_date >= '2020-01-01'", name="ck_expected_incomes_due_date_min_2020_01_01"),
        sa.CheckConstraint("budget_month >= 1 AND budget_month <= 12", name="ck_expected_incomes_budget_month_1_12"),
        sa.CheckConstraint("budget_year >= 2020", name="ck_expected_incomes_budget_year_min_2020"),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["source_id"], ["income_sources.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_expected_incomes_id"), "expected_incomes", ["id"], unique=False)
    op.create_index(op.f("ix_expected_incomes_owner_id"), "expected_incomes", ["owner_id"], unique=False)
    op.create_index(op.f("ix_expected_incomes_source_id"), "expected_incomes", ["source_id"], unique=False)
    op.create_index(
        "ix_expected_incomes_owner_month_status",
        "expected_incomes",
        ["owner_id", "budget_year", "budget_month", "status"],
        unique=False,
    )
    op.create_index(
        "ix_expected_incomes_owner_source",
        "expected_incomes",
        ["owner_id", "source_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_expected_incomes_owner_source", table_name="expected_incomes")
    op.drop_index("ix_expected_incomes_owner_month_status", table_name="expected_incomes")
    op.drop_index(op.f("ix_expected_incomes_source_id"), table_name="expected_incomes")
    op.drop_index(op.f("ix_expected_incomes_owner_id"), table_name="expected_incomes")
    op.drop_index(op.f("ix_expected_incomes_id"), table_name="expected_incomes")
    op.drop_table("expected_incomes")
    expected_income_status.drop(op.get_bind(), checkfirst=True)
