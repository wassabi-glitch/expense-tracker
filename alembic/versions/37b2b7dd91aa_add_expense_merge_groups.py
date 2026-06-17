"""add expense merge groups

Revision ID: 37b2b7dd91aa
Revises: 2f4c8d9e7a11
Create Date: 2026-05-16 18:20:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "37b2b7dd91aa"
down_revision: Union[str, Sequence[str], None] = "2f4c8d9e7a11"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "expense_merge_groups",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("owner_id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=100), nullable=False),
        sa.Column("description", sa.String(length=500), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_expense_merge_groups_id"), "expense_merge_groups", ["id"], unique=False)
    op.create_index(op.f("ix_expense_merge_groups_owner_id"), "expense_merge_groups", ["owner_id"], unique=False)
    op.create_index(
        "ix_expense_merge_groups_owner_created",
        "expense_merge_groups",
        ["owner_id", "created_at"],
        unique=False,
    )

    op.add_column("financial_events", sa.Column("merge_group_id", sa.Integer(), nullable=True))
    op.create_index(op.f("ix_financial_events_merge_group_id"), "financial_events", ["merge_group_id"], unique=False)
    op.create_foreign_key(
        "fk_financial_events_merge_group_id_expense_merge_groups",
        "financial_events",
        "expense_merge_groups",
        ["merge_group_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint("fk_financial_events_merge_group_id_expense_merge_groups", "financial_events", type_="foreignkey")
    op.drop_index(op.f("ix_financial_events_merge_group_id"), table_name="financial_events")
    op.drop_column("financial_events", "merge_group_id")

    op.drop_index("ix_expense_merge_groups_owner_created", table_name="expense_merge_groups")
    op.drop_index(op.f("ix_expense_merge_groups_owner_id"), table_name="expense_merge_groups")
    op.drop_index(op.f("ix_expense_merge_groups_id"), table_name="expense_merge_groups")
    op.drop_table("expense_merge_groups")
