"""add isolated project subcategory ledger links

Revision ID: fe7a8b9c0d12
Revises: 1a2b3c4d5e6f
Create Date: 2026-07-04 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "fe7a8b9c0d12"
down_revision: Union[str, Sequence[str], None] = "1a2b3c4d5e6f"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "entity_ledger",
        sa.Column("isolated_project_subcategory_id", sa.Integer(), nullable=True),
    )
    op.create_index(
        "ix_entity_ledger_isolated_project_subcategory_id",
        "entity_ledger",
        ["isolated_project_subcategory_id"],
    )
    op.create_foreign_key(
        "fk_entity_ledger_isolated_project_subcategory_id",
        "entity_ledger",
        "isolated_project_subcategory_allocations",
        ["isolated_project_subcategory_id"],
        ["id"],
        ondelete="SET NULL",
    )

    op.add_column(
        "expense_session_draft_items",
        sa.Column("isolated_project_subcategory_id", sa.Integer(), nullable=True),
    )
    op.create_index(
        "ix_expense_session_draft_items_isolated_project_subcategory_id",
        "expense_session_draft_items",
        ["isolated_project_subcategory_id"],
    )
    op.create_foreign_key(
        "fk_expense_session_draft_items_isolated_project_subcategory_id",
        "expense_session_draft_items",
        "isolated_project_subcategory_allocations",
        ["isolated_project_subcategory_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint(
        "fk_expense_session_draft_items_isolated_project_subcategory_id",
        "expense_session_draft_items",
        type_="foreignkey",
    )
    op.drop_index(
        "ix_expense_session_draft_items_isolated_project_subcategory_id",
        table_name="expense_session_draft_items",
    )
    op.drop_column("expense_session_draft_items", "isolated_project_subcategory_id")

    op.drop_constraint(
        "fk_entity_ledger_isolated_project_subcategory_id",
        "entity_ledger",
        type_="foreignkey",
    )
    op.drop_index(
        "ix_entity_ledger_isolated_project_subcategory_id",
        table_name="entity_ledger",
    )
    op.drop_column("entity_ledger", "isolated_project_subcategory_id")
