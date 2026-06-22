"""g30 recurring occurrence foundation

Revision ID: a0b1c2d3e4f6
Revises: 9e0f1a2b3c45
Create Date: 2026-06-22 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "a0b1c2d3e4f6"
down_revision: Union[str, Sequence[str], None] = "9e0f1a2b3c45"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


RECORDING_MODES = ("CONFIRM_EACH", "AUTO_RECORD")
OCCURRENCE_STATUSES = (
    "PENDING_CONFIRMATION",
    "AUTO_POST_FAILED",
    "FULFILLED",
    "SKIPPED",
    "CANCELLED",
)
EXPENSE_CATEGORIES = (
    "GROCERIES",
    "DINING_OUT",
    "ELECTRONICS",
    "HOUSING",
    "UTILITIES",
    "SUBSCRIPTIONS",
    "TRANSPORT",
    "HEALTH",
    "PERSONAL_CARE",
    "EDUCATION",
    "CLOTHING",
    "FAMILY_EVENTS",
    "ENTERTAINMENT",
    "INSTALLMENTS_DEBT",
    "BUSINESS_WORK",
    "BANK_FEES_INTEREST",
    "TRAVEL",
    "CHARITY",
    "ANIMALS_PETS",
    "DEBT_CHARGES",
)


def upgrade() -> None:
    bind = op.get_bind()
    recording_mode = postgresql.ENUM(*RECORDING_MODES, name="recurringrecordingmode")
    occurrence_status = postgresql.ENUM(*OCCURRENCE_STATUSES, name="recurringoccurrencestatus")
    recording_mode.create(bind, checkfirst=True)
    occurrence_status.create(bind, checkfirst=True)

    recording_mode_column = postgresql.ENUM(
        *RECORDING_MODES,
        name="recurringrecordingmode",
        create_type=False,
    )
    occurrence_status_column = postgresql.ENUM(
        *OCCURRENCE_STATUSES,
        name="recurringoccurrencestatus",
        create_type=False,
    )
    expense_category = postgresql.ENUM(
        *EXPENSE_CATEGORIES,
        name="expensecategory",
        create_type=False,
    )

    op.add_column(
        "recurring_expenses",
        sa.Column(
            "recording_mode",
            recording_mode_column,
            server_default=sa.text("'AUTO_RECORD'::recurringrecordingmode"),
            nullable=False,
        ),
    )
    op.add_column(
        "recurring_expenses",
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "recurring_expenses",
        sa.Column("paused_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index(
        "ix_recurring_expenses_archived_at",
        "recurring_expenses",
        ["archived_at"],
    )

    op.create_table(
        "recurring_occurrences",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("owner_id", sa.Integer(), nullable=False),
        sa.Column("template_id", sa.Integer(), nullable=False),
        sa.Column("scheduled_due_date", sa.Date(), nullable=False),
        sa.Column("expected_title", sa.String(length=32), nullable=False),
        sa.Column("expected_amount", sa.BigInteger(), nullable=False),
        sa.Column("expected_category", expense_category, nullable=False),
        sa.Column(
            "status",
            occurrence_status_column,
            server_default=sa.text("'PENDING_CONFIRMATION'::recurringoccurrencestatus"),
            nullable=False,
        ),
        sa.Column("actual_amount", sa.BigInteger(), nullable=True),
        sa.Column("actual_date", sa.Date(), nullable=True),
        sa.Column("linked_financial_event_id", sa.Integer(), nullable=True),
        sa.Column("initial_notified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("remind_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("failure_code", sa.String(length=100), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "expected_amount > 0",
            name="ck_recurring_occurrences_expected_amount_positive",
        ),
        sa.CheckConstraint(
            "actual_amount IS NULL OR actual_amount > 0",
            name="ck_recurring_occurrences_actual_amount_positive",
        ),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["template_id"],
            ["recurring_expenses.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["linked_financial_event_id"],
            ["financial_events.id"],
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "template_id",
            "scheduled_due_date",
            name="uq_recurring_occurrences_template_due_date",
        ),
    )
    op.create_index(
        op.f("ix_recurring_occurrences_id"),
        "recurring_occurrences",
        ["id"],
    )
    op.create_index(
        op.f("ix_recurring_occurrences_owner_id"),
        "recurring_occurrences",
        ["owner_id"],
    )
    op.create_index(
        op.f("ix_recurring_occurrences_template_id"),
        "recurring_occurrences",
        ["template_id"],
    )
    op.create_index(
        op.f("ix_recurring_occurrences_scheduled_due_date"),
        "recurring_occurrences",
        ["scheduled_due_date"],
    )
    op.create_index(
        op.f("ix_recurring_occurrences_linked_financial_event_id"),
        "recurring_occurrences",
        ["linked_financial_event_id"],
    )
    op.create_index(
        "ix_recurring_occurrences_owner_status",
        "recurring_occurrences",
        ["owner_id", "status"],
    )
    op.create_index(
        "ix_recurring_occurrences_owner_due_date",
        "recurring_occurrences",
        ["owner_id", "scheduled_due_date"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_recurring_occurrences_owner_due_date",
        table_name="recurring_occurrences",
    )
    op.drop_index(
        "ix_recurring_occurrences_owner_status",
        table_name="recurring_occurrences",
    )
    op.drop_index(
        op.f("ix_recurring_occurrences_linked_financial_event_id"),
        table_name="recurring_occurrences",
    )
    op.drop_index(
        op.f("ix_recurring_occurrences_scheduled_due_date"),
        table_name="recurring_occurrences",
    )
    op.drop_index(
        op.f("ix_recurring_occurrences_template_id"),
        table_name="recurring_occurrences",
    )
    op.drop_index(
        op.f("ix_recurring_occurrences_owner_id"),
        table_name="recurring_occurrences",
    )
    op.drop_index(
        op.f("ix_recurring_occurrences_id"),
        table_name="recurring_occurrences",
    )
    op.drop_table("recurring_occurrences")

    op.drop_index("ix_recurring_expenses_archived_at", table_name="recurring_expenses")
    op.drop_column("recurring_expenses", "paused_at")
    op.drop_column("recurring_expenses", "archived_at")
    op.drop_column("recurring_expenses", "recording_mode")

    bind = op.get_bind()
    postgresql.ENUM(name="recurringoccurrencestatus").drop(bind, checkfirst=True)
    postgresql.ENUM(name="recurringrecordingmode").drop(bind, checkfirst=True)
