"""add expense session drafts

Revision ID: 2f4c8d9e7a11
Revises: 18c1e7e399cd
Create Date: 2026-05-16 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = "2f4c8d9e7a11"
down_revision: Union[str, Sequence[str], None] = "18c1e7e399cd"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


expense_session_draft_status = postgresql.ENUM(
    "ACTIVE",
    "PAUSED",
    "FINALIZED",
    "ABANDONED",
    name="expensesessiondraftstatus",
    create_type=False,
)
expense_session_draft_source = postgresql.ENUM(
    "MANUAL",
    "OCR",
    name="expensesessiondraftsource",
    create_type=False,
)
expense_category_enum = postgresql.ENUM(
    "GROCERIES", "DINING_OUT", "ELECTRONICS", "HOUSING", "UTILITIES",
    "SUBSCRIPTIONS", "TRANSPORT", "HEALTH", "PERSONAL_CARE", "EDUCATION",
    "CLOTHING", "FAMILY_EVENTS", "ENTERTAINMENT", "INSTALLMENTS_DEBT",
    "BUSINESS_WORK", "BANK_FEES_INTEREST", "DEBT_CHARGES", "TRAVEL",
    "CHARITY", "ANIMALS_PETS",
    name="expensecategory",
    create_type=False,
)


def upgrade() -> None:
    expense_session_draft_status.create(op.get_bind(), checkfirst=True)
    expense_session_draft_source.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "expense_session_drafts",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("owner_id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=100), nullable=False),
        sa.Column("description", sa.String(length=500), nullable=True),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("amount_paid", sa.BigInteger(), nullable=True),
        sa.Column("status", expense_session_draft_status, nullable=False),
        sa.Column("source_type", expense_session_draft_source, nullable=False),
        sa.Column("raw_ocr_text", sa.String(), nullable=True),
        sa.Column("finalized_event_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("amount_paid IS NULL OR amount_paid > 0", name="ck_expense_session_drafts_amount_paid_positive"),
        sa.ForeignKeyConstraint(["finalized_event_id"], ["financial_events.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_expense_session_drafts_id"), "expense_session_drafts", ["id"], unique=False)
    op.create_index(op.f("ix_expense_session_drafts_owner_id"), "expense_session_drafts", ["owner_id"], unique=False)
    op.create_index(op.f("ix_expense_session_drafts_finalized_event_id"), "expense_session_drafts", ["finalized_event_id"], unique=False)
    op.create_index("ix_expense_session_drafts_owner_status", "expense_session_drafts", ["owner_id", "status"], unique=False)

    op.create_table(
        "expense_session_draft_items",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("draft_id", sa.Integer(), nullable=False),
        sa.Column("owner_id", sa.Integer(), nullable=False),
        sa.Column("label", sa.String(length=100), nullable=False),
        sa.Column("original_amount", sa.BigInteger(), nullable=False),
        sa.Column("category", expense_category_enum, nullable=False),
        sa.Column("subcategory_id", sa.Integer(), nullable=True),
        sa.Column("project_id", sa.Integer(), nullable=True),
        sa.Column("sort_order", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("original_amount > 0", name="ck_expense_session_draft_items_original_amount_positive"),
        sa.ForeignKeyConstraint(["draft_id"], ["expense_session_drafts.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["subcategory_id"], ["user_subcategories.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_expense_session_draft_items_id"), "expense_session_draft_items", ["id"], unique=False)
    op.create_index(op.f("ix_expense_session_draft_items_draft_id"), "expense_session_draft_items", ["draft_id"], unique=False)
    op.create_index(op.f("ix_expense_session_draft_items_owner_id"), "expense_session_draft_items", ["owner_id"], unique=False)

    op.create_table(
        "expense_session_draft_wallet_allocations",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("draft_id", sa.Integer(), nullable=False),
        sa.Column("owner_id", sa.Integer(), nullable=False),
        sa.Column("wallet_id", sa.Integer(), nullable=False),
        sa.Column("amount", sa.BigInteger(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("amount > 0", name="ck_expense_session_draft_wallet_allocations_amount_positive"),
        sa.ForeignKeyConstraint(["draft_id"], ["expense_session_drafts.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["wallet_id"], ["wallets.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("draft_id", "wallet_id", name="uq_expense_session_draft_wallet_allocations_draft_wallet"),
    )
    op.create_index(op.f("ix_expense_session_draft_wallet_allocations_id"), "expense_session_draft_wallet_allocations", ["id"], unique=False)
    op.create_index(op.f("ix_expense_session_draft_wallet_allocations_draft_id"), "expense_session_draft_wallet_allocations", ["draft_id"], unique=False)
    op.create_index(op.f("ix_expense_session_draft_wallet_allocations_owner_id"), "expense_session_draft_wallet_allocations", ["owner_id"], unique=False)
    op.create_index(op.f("ix_expense_session_draft_wallet_allocations_wallet_id"), "expense_session_draft_wallet_allocations", ["wallet_id"], unique=False)

    op.create_table(
        "expense_session_draft_splits",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("draft_id", sa.Integer(), nullable=False),
        sa.Column("owner_id", sa.Integer(), nullable=False),
        sa.Column("contact_name", sa.String(length=32), nullable=False),
        sa.Column("amount", sa.BigInteger(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("amount > 0", name="ck_expense_session_draft_splits_amount_positive"),
        sa.ForeignKeyConstraint(["draft_id"], ["expense_session_drafts.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_expense_session_draft_splits_id"), "expense_session_draft_splits", ["id"], unique=False)
    op.create_index(op.f("ix_expense_session_draft_splits_draft_id"), "expense_session_draft_splits", ["draft_id"], unique=False)
    op.create_index(op.f("ix_expense_session_draft_splits_owner_id"), "expense_session_draft_splits", ["owner_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_expense_session_draft_splits_owner_id"), table_name="expense_session_draft_splits")
    op.drop_index(op.f("ix_expense_session_draft_splits_draft_id"), table_name="expense_session_draft_splits")
    op.drop_index(op.f("ix_expense_session_draft_splits_id"), table_name="expense_session_draft_splits")
    op.drop_table("expense_session_draft_splits")

    op.drop_index(op.f("ix_expense_session_draft_wallet_allocations_wallet_id"), table_name="expense_session_draft_wallet_allocations")
    op.drop_index(op.f("ix_expense_session_draft_wallet_allocations_owner_id"), table_name="expense_session_draft_wallet_allocations")
    op.drop_index(op.f("ix_expense_session_draft_wallet_allocations_draft_id"), table_name="expense_session_draft_wallet_allocations")
    op.drop_index(op.f("ix_expense_session_draft_wallet_allocations_id"), table_name="expense_session_draft_wallet_allocations")
    op.drop_table("expense_session_draft_wallet_allocations")

    op.drop_index(op.f("ix_expense_session_draft_items_owner_id"), table_name="expense_session_draft_items")
    op.drop_index(op.f("ix_expense_session_draft_items_draft_id"), table_name="expense_session_draft_items")
    op.drop_index(op.f("ix_expense_session_draft_items_id"), table_name="expense_session_draft_items")
    op.drop_table("expense_session_draft_items")

    op.drop_index("ix_expense_session_drafts_owner_status", table_name="expense_session_drafts")
    op.drop_index(op.f("ix_expense_session_drafts_finalized_event_id"), table_name="expense_session_drafts")
    op.drop_index(op.f("ix_expense_session_drafts_owner_id"), table_name="expense_session_drafts")
    op.drop_index(op.f("ix_expense_session_drafts_id"), table_name="expense_session_drafts")
    op.drop_table("expense_session_drafts")

    expense_session_draft_source.drop(op.get_bind(), checkfirst=True)
    expense_session_draft_status.drop(op.get_bind(), checkfirst=True)
