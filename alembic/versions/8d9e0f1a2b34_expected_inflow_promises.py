"""expected inflow promise aggregates

Revision ID: 8d9e0f1a2b34
Revises: 7b8c9d0e1f23
Create Date: 2026-06-21 09:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "8d9e0f1a2b34"
down_revision: Union[str, Sequence[str], None] = "7b8c9d0e1f23"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


promise_status = sa.Enum(
    "EXPECTED",
    "PARTIALLY_RECEIVED",
    "RESOLVED",
    "CANCELLED",
    "WRITTEN_OFF",
    name="expectedinflowpromisestatus",
)


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.execute("ALTER TYPE expectedincomestatus ADD VALUE IF NOT EXISTS 'SUPERSEDED'")
        op.execute("ALTER TYPE expectedincomestatus ADD VALUE IF NOT EXISTS 'WRITTEN_OFF'")

    op.create_table(
        "expected_inflow_promises",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("owner_id", sa.Integer(), nullable=False),
        sa.Column("kind", sa.String(length=32), nullable=False),
        sa.Column("source_id", sa.Integer(), nullable=True),
        sa.Column("debt_id", sa.Integer(), nullable=True),
        sa.Column("asset_id", sa.Integer(), nullable=True),
        sa.Column("refund_event_id", sa.Integer(), nullable=True),
        sa.Column("title", sa.String(length=100), nullable=False),
        sa.Column("original_amount", sa.BigInteger(), nullable=False),
        sa.Column("status", promise_status, nullable=False),
        sa.Column("backing_eligible", sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.Column("note", sa.String(length=200), nullable=True),
        sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("original_amount > 0", name="ck_expected_inflow_promises_amount_positive"),
        sa.CheckConstraint("original_amount <= 999999999999", name="ck_expected_inflow_promises_amount_limit"),
        sa.CheckConstraint(
            "(CASE WHEN source_id IS NOT NULL THEN 1 ELSE 0 END + "
            "CASE WHEN debt_id IS NOT NULL THEN 1 ELSE 0 END + "
            "CASE WHEN asset_id IS NOT NULL THEN 1 ELSE 0 END + "
            "CASE WHEN refund_event_id IS NOT NULL THEN 1 ELSE 0 END) = 1",
            name="ck_expected_inflow_promises_exactly_one_source",
        ),
        sa.ForeignKeyConstraint(["asset_id"], ["assets.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["debt_id"], ["debts.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["refund_event_id"], ["financial_events.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["source_id"], ["income_sources.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_expected_inflow_promises_id"), "expected_inflow_promises", ["id"])
    op.create_index(op.f("ix_expected_inflow_promises_owner_id"), "expected_inflow_promises", ["owner_id"])
    op.create_index(op.f("ix_expected_inflow_promises_kind"), "expected_inflow_promises", ["kind"])
    op.create_index(op.f("ix_expected_inflow_promises_source_id"), "expected_inflow_promises", ["source_id"])
    op.create_index(op.f("ix_expected_inflow_promises_debt_id"), "expected_inflow_promises", ["debt_id"])
    op.create_index(op.f("ix_expected_inflow_promises_asset_id"), "expected_inflow_promises", ["asset_id"])
    op.create_index(op.f("ix_expected_inflow_promises_refund_event_id"), "expected_inflow_promises", ["refund_event_id"])
    op.create_index("ix_expected_inflow_promises_owner_status", "expected_inflow_promises", ["owner_id", "status"])
    op.create_index("ix_expected_inflow_promises_owner_kind", "expected_inflow_promises", ["owner_id", "kind"])

    op.add_column("expected_incomes", sa.Column("promise_id", sa.Integer(), nullable=True))
    op.add_column("expected_inflow_realizations", sa.Column("promise_id", sa.Integer(), nullable=True))

    op.execute(
        """
        INSERT INTO expected_inflow_promises (
            id, owner_id, kind, source_id, debt_id, asset_id, refund_event_id,
            title, original_amount, status, backing_eligible, note, closed_at,
            created_at, updated_at
        )
        SELECT
            root.id,
            root.owner_id,
            root.kind,
            root.source_id,
            root.debt_id,
            root.asset_id,
            root.refund_event_id,
            COALESCE(
                (SELECT name FROM income_sources WHERE id = root.source_id),
                (SELECT counterparty_name FROM debts WHERE id = root.debt_id),
                (SELECT title FROM assets WHERE id = root.asset_id),
                (SELECT title FROM financial_events WHERE id = root.refund_event_id),
                'Expected inflow'
            ),
            root.amount,
            CAST(CASE
                WHEN CAST(root.status AS VARCHAR) = 'CANCELLED' OR CAST(root.status AS VARCHAR) = 'MISSED' THEN 'CANCELLED'
                WHEN root.close_reason = 'RESCHEDULED' AND COALESCE(root.received_amount, 0) > 0 THEN 'PARTIALLY_RECEIVED'
                WHEN root.close_reason = 'RESCHEDULED' THEN 'EXPECTED'
                WHEN CAST(root.status AS VARCHAR) = 'RECEIVED' OR CAST(root.status AS VARCHAR) = 'RESOLVED' THEN 'RESOLVED'
                WHEN CAST(root.status AS VARCHAR) = 'PARTIALLY_RECEIVED' THEN 'PARTIALLY_RECEIVED'
                ELSE 'EXPECTED'
            END AS expectedinflowpromisestatus),
            root.backing_eligible,
            root.note,
            CASE WHEN root.close_reason = 'RESCHEDULED' THEN NULL ELSE root.closed_at END,
            root.created_at,
            root.updated_at
        FROM expected_incomes AS root
        WHERE root.parent_id IS NULL
        """
    )
    op.execute(
        """
        WITH RECURSIVE schedule_tree AS (
            SELECT id, id AS root_id
            FROM expected_incomes
            WHERE parent_id IS NULL
            UNION ALL
            SELECT child.id, schedule_tree.root_id
            FROM expected_incomes AS child
            JOIN schedule_tree ON child.parent_id = schedule_tree.id
        )
        UPDATE expected_incomes
        SET promise_id = (
            SELECT root_id FROM schedule_tree WHERE schedule_tree.id = expected_incomes.id
        )
        """
    )
    op.execute(
        """
        UPDATE expected_inflow_realizations
        SET promise_id = (
            SELECT MIN(schedule.promise_id)
            FROM expected_inflow_realization_allocations AS allocation
            JOIN expected_incomes AS schedule ON schedule.id = allocation.expected_inflow_id
            WHERE allocation.realization_id = expected_inflow_realizations.id
            HAVING MIN(schedule.promise_id) = MAX(schedule.promise_id)
        )
        """
    )

    if bind.dialect.name == "postgresql":
        op.execute(
            "SELECT setval(pg_get_serial_sequence('expected_inflow_promises', 'id'), "
            "COALESCE((SELECT MAX(id) FROM expected_inflow_promises), 1), "
            "EXISTS (SELECT 1 FROM expected_inflow_promises))"
        )

    op.alter_column("expected_incomes", "promise_id", existing_type=sa.Integer(), nullable=False)
    op.create_foreign_key(
        "fk_expected_incomes_promise_id",
        "expected_incomes",
        "expected_inflow_promises",
        ["promise_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_foreign_key(
        "fk_expected_inflow_realizations_promise_id",
        "expected_inflow_realizations",
        "expected_inflow_promises",
        ["promise_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_index(op.f("ix_expected_incomes_promise_id"), "expected_incomes", ["promise_id"])
    op.create_index(op.f("ix_expected_inflow_realizations_promise_id"), "expected_inflow_realizations", ["promise_id"])

    op.create_table(
        "expected_inflow_write_offs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("owner_id", sa.Integer(), nullable=False),
        sa.Column("promise_id", sa.Integer(), nullable=False),
        sa.Column("schedule_id", sa.Integer(), nullable=False),
        sa.Column("amount", sa.BigInteger(), nullable=False),
        sa.Column("reason", sa.String(length=200), nullable=False),
        sa.Column("written_off_date", sa.Date(), nullable=False),
        sa.Column("reversed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("reversal_note", sa.String(length=200), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("amount > 0", name="ck_expected_inflow_write_offs_amount_positive"),
        sa.CheckConstraint("amount <= 999999999999", name="ck_expected_inflow_write_offs_amount_limit"),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["promise_id"], ["expected_inflow_promises.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["schedule_id"], ["expected_incomes.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_expected_inflow_write_offs_id"), "expected_inflow_write_offs", ["id"])
    op.create_index(op.f("ix_expected_inflow_write_offs_owner_id"), "expected_inflow_write_offs", ["owner_id"])
    op.create_index(op.f("ix_expected_inflow_write_offs_promise_id"), "expected_inflow_write_offs", ["promise_id"])
    op.create_index(op.f("ix_expected_inflow_write_offs_schedule_id"), "expected_inflow_write_offs", ["schedule_id"])
    op.create_index(
        "ix_expected_inflow_write_offs_promise_date",
        "expected_inflow_write_offs",
        ["promise_id", "written_off_date"],
    )


def downgrade() -> None:
    op.drop_index("ix_expected_inflow_write_offs_promise_date", table_name="expected_inflow_write_offs")
    op.drop_index(op.f("ix_expected_inflow_write_offs_schedule_id"), table_name="expected_inflow_write_offs")
    op.drop_index(op.f("ix_expected_inflow_write_offs_promise_id"), table_name="expected_inflow_write_offs")
    op.drop_index(op.f("ix_expected_inflow_write_offs_owner_id"), table_name="expected_inflow_write_offs")
    op.drop_index(op.f("ix_expected_inflow_write_offs_id"), table_name="expected_inflow_write_offs")
    op.drop_table("expected_inflow_write_offs")

    op.drop_index(op.f("ix_expected_inflow_realizations_promise_id"), table_name="expected_inflow_realizations")
    op.drop_index(op.f("ix_expected_incomes_promise_id"), table_name="expected_incomes")
    op.drop_constraint("fk_expected_inflow_realizations_promise_id", "expected_inflow_realizations", type_="foreignkey")
    op.drop_constraint("fk_expected_incomes_promise_id", "expected_incomes", type_="foreignkey")
    op.drop_column("expected_inflow_realizations", "promise_id")
    op.drop_column("expected_incomes", "promise_id")

    op.drop_index("ix_expected_inflow_promises_owner_kind", table_name="expected_inflow_promises")
    op.drop_index("ix_expected_inflow_promises_owner_status", table_name="expected_inflow_promises")
    op.drop_index(op.f("ix_expected_inflow_promises_refund_event_id"), table_name="expected_inflow_promises")
    op.drop_index(op.f("ix_expected_inflow_promises_asset_id"), table_name="expected_inflow_promises")
    op.drop_index(op.f("ix_expected_inflow_promises_debt_id"), table_name="expected_inflow_promises")
    op.drop_index(op.f("ix_expected_inflow_promises_source_id"), table_name="expected_inflow_promises")
    op.drop_index(op.f("ix_expected_inflow_promises_kind"), table_name="expected_inflow_promises")
    op.drop_index(op.f("ix_expected_inflow_promises_owner_id"), table_name="expected_inflow_promises")
    op.drop_index(op.f("ix_expected_inflow_promises_id"), table_name="expected_inflow_promises")
    op.drop_table("expected_inflow_promises")
    promise_status.drop(op.get_bind(), checkfirst=True)

    # PostgreSQL enum labels are retained because removing them requires rebuilding the type.
