"""add income ledger tables

Revision ID: d3a6f5e2b1c9
Revises: c1bce7a2d116
Create Date: 2026-03-10 18:45:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "d3a6f5e2b1c9"
down_revision: Union[str, Sequence[str], None] = "c1bce7a2d116"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "income_sources",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("owner_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=64), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("owner_id", "name", name="uq_income_sources_owner_name"),
    )
    op.create_index(op.f("ix_income_sources_id"), "income_sources", ["id"], unique=False)
    op.create_index(op.f("ix_income_sources_owner_id"), "income_sources", ["owner_id"], unique=False)

    op.create_table(
        "income_entries",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("owner_id", sa.Integer(), nullable=False),
        sa.Column("source_id", sa.Integer(), nullable=True),
        sa.Column("amount", sa.BigInteger(), nullable=False),
        sa.Column("note", sa.String(length=500), nullable=True),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("amount > 0", name="ck_income_entries_amount_positive"),
        sa.CheckConstraint("date >= '2020-01-01'", name="ck_income_entries_date_min_2020_01_01"),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["source_id"], ["income_sources.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_income_entries_id"), "income_entries", ["id"], unique=False)
    op.create_index(op.f("ix_income_entries_owner_id"), "income_entries", ["owner_id"], unique=False)
    op.create_index(op.f("ix_income_entries_source_id"), "income_entries", ["source_id"], unique=False)
    op.create_index("ix_income_entries_owner_date", "income_entries", ["owner_id", "date"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_income_entries_owner_date", table_name="income_entries")
    op.drop_index(op.f("ix_income_entries_source_id"), table_name="income_entries")
    op.drop_index(op.f("ix_income_entries_owner_id"), table_name="income_entries")
    op.drop_index(op.f("ix_income_entries_id"), table_name="income_entries")
    op.drop_table("income_entries")

    op.drop_index(op.f("ix_income_sources_owner_id"), table_name="income_sources")
    op.drop_index(op.f("ix_income_sources_id"), table_name="income_sources")
    op.drop_table("income_sources")
