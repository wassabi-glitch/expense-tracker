"""add project subcategories

Revision ID: b7e1c2d4f9aa
Revises: 8f2c44dbe93a
Create Date: 2026-05-18 18:20:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = "b7e1c2d4f9aa"
down_revision: Union[str, Sequence[str], None] = "8f2c44dbe93a"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    expense_category_enum = postgresql.ENUM(
        "FOOD",
        "TRANSPORT",
        "ENTERTAINMENT",
        "BILLS",
        "HEALTH",
        "SHOPPING",
        "EDUCATION",
        "SAVINGS",
        "OTHER",
        "BUSINESS_WORK",
        "ELECTRONICS",
        "PERSONAL_CARE",
        name="expensecategory",
        create_type=False,
    )
    op.create_table(
        "project_subcategories",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("project_id", sa.Integer(), nullable=False),
        sa.Column("category", expense_category_enum, nullable=False),
        sa.Column("name", sa.String(length=50), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("limit_amount", sa.BigInteger(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("project_id", "category", "name", name="uq_project_subcategories_project_category_name"),
    )
    op.create_index("ix_project_subcategories_project_category", "project_subcategories", ["project_id", "category"], unique=False)
    op.create_index(op.f("ix_project_subcategories_id"), "project_subcategories", ["id"], unique=False)
    op.create_index(op.f("ix_project_subcategories_project_id"), "project_subcategories", ["project_id"], unique=False)

    op.add_column("expense_session_draft_items", sa.Column("project_subcategory_id", sa.Integer(), nullable=True))
    op.create_index(
        op.f("ix_expense_session_draft_items_project_subcategory_id"),
        "expense_session_draft_items",
        ["project_subcategory_id"],
        unique=False,
    )
    op.create_foreign_key(
        "fk_expense_session_draft_items_project_subcategory_id",
        "expense_session_draft_items",
        "project_subcategories",
        ["project_subcategory_id"],
        ["id"],
        ondelete="SET NULL",
    )

    op.add_column("entity_ledger", sa.Column("project_subcategory_id", sa.Integer(), nullable=True))
    op.create_index(op.f("ix_entity_ledger_project_subcategory_id"), "entity_ledger", ["project_subcategory_id"], unique=False)
    op.create_foreign_key(
        "fk_entity_ledger_project_subcategory_id",
        "entity_ledger",
        "project_subcategories",
        ["project_subcategory_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint("fk_entity_ledger_project_subcategory_id", "entity_ledger", type_="foreignkey")
    op.drop_index(op.f("ix_entity_ledger_project_subcategory_id"), table_name="entity_ledger")
    op.drop_column("entity_ledger", "project_subcategory_id")

    op.drop_constraint("fk_expense_session_draft_items_project_subcategory_id", "expense_session_draft_items", type_="foreignkey")
    op.drop_index(op.f("ix_expense_session_draft_items_project_subcategory_id"), table_name="expense_session_draft_items")
    op.drop_column("expense_session_draft_items", "project_subcategory_id")

    op.drop_index(op.f("ix_project_subcategories_project_id"), table_name="project_subcategories")
    op.drop_index(op.f("ix_project_subcategories_id"), table_name="project_subcategories")
    op.drop_index("ix_project_subcategories_project_category", table_name="project_subcategories")
    op.drop_table("project_subcategories")
