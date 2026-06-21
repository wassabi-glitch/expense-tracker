"""g29 expected inflow machine

Revision ID: 7b8c9d0e1f23
Revises: 6a7b8c9d0e12
Create Date: 2026-06-20 16:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "7b8c9d0e1f23"
down_revision: Union[str, Sequence[str], None] = "6a7b8c9d0e12"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.execute("ALTER TYPE expectedincomestatus ADD VALUE IF NOT EXISTS 'PARTIALLY_RECEIVED'")
        op.execute("ALTER TYPE expectedincomestatus ADD VALUE IF NOT EXISTS 'RESOLVED'")

    op.add_column("expected_incomes", sa.Column("kind", sa.String(length=32), nullable=True))
    op.add_column("expected_incomes", sa.Column("asset_id", sa.Integer(), nullable=True))
    op.add_column("expected_incomes", sa.Column("refund_event_id", sa.Integer(), nullable=True))
    op.add_column("expected_incomes", sa.Column("parent_id", sa.Integer(), nullable=True))
    op.add_column(
        "expected_incomes",
        sa.Column("backing_eligible", sa.Boolean(), server_default=sa.true(), nullable=False),
    )
    op.add_column("expected_incomes", sa.Column("close_reason", sa.String(length=32), nullable=True))
    op.add_column("expected_incomes", sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True))

    op.execute(
        "UPDATE expected_incomes "
        "SET kind = CASE WHEN debt_id IS NOT NULL THEN 'RECEIVABLE' ELSE 'EARNED' END, "
        "received_amount = COALESCE(received_amount, 0), "
        "close_reason = CASE "
        "WHEN status = 'RECEIVED' THEN 'LEGACY_RECEIVED' "
        "WHEN status = 'MISSED' THEN 'LEGACY_MISSED' "
        "WHEN status = 'CANCELLED' THEN 'CANCELLED' "
        "ELSE close_reason END"
    )
    op.alter_column("expected_incomes", "kind", existing_type=sa.String(length=32), nullable=False)

    op.create_foreign_key(
        "fk_expected_incomes_asset_id_assets",
        "expected_incomes",
        "assets",
        ["asset_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_foreign_key(
        "fk_expected_incomes_refund_event_id_financial_events",
        "expected_incomes",
        "financial_events",
        ["refund_event_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_foreign_key(
        "fk_expected_incomes_parent_id_expected_incomes",
        "expected_incomes",
        "expected_incomes",
        ["parent_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_check_constraint(
        "ck_expected_incomes_exactly_one_source",
        "expected_incomes",
        "(CASE WHEN source_id IS NOT NULL THEN 1 ELSE 0 END + "
        "CASE WHEN debt_id IS NOT NULL THEN 1 ELSE 0 END + "
        "CASE WHEN asset_id IS NOT NULL THEN 1 ELSE 0 END + "
        "CASE WHEN refund_event_id IS NOT NULL THEN 1 ELSE 0 END) = 1",
    )
    op.create_index(op.f("ix_expected_incomes_kind"), "expected_incomes", ["kind"], unique=False)
    op.create_index(op.f("ix_expected_incomes_asset_id"), "expected_incomes", ["asset_id"], unique=False)
    op.create_index(
        op.f("ix_expected_incomes_refund_event_id"),
        "expected_incomes",
        ["refund_event_id"],
        unique=False,
    )
    op.create_index(op.f("ix_expected_incomes_parent_id"), "expected_incomes", ["parent_id"], unique=False)
    op.create_index(
        "ix_expected_incomes_owner_kind_status",
        "expected_incomes",
        ["owner_id", "kind", "status"],
        unique=False,
    )

    op.create_table(
        "expected_inflow_realizations",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("owner_id", sa.Integer(), nullable=False),
        sa.Column("actual_amount", sa.BigInteger(), nullable=False),
        sa.Column("received_date", sa.Date(), nullable=False),
        sa.Column("note", sa.String(length=200), nullable=True),
        sa.Column("idempotency_key", sa.String(length=64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint(
            "actual_amount > 0",
            name="ck_expected_inflow_realizations_amount_positive",
        ),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "owner_id",
            "idempotency_key",
            name="uq_expected_inflow_realizations_owner_idempotency",
        ),
    )
    op.create_index(
        op.f("ix_expected_inflow_realizations_id"),
        "expected_inflow_realizations",
        ["id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_expected_inflow_realizations_owner_id"),
        "expected_inflow_realizations",
        ["owner_id"],
        unique=False,
    )
    op.create_index(
        "ix_expected_inflow_realizations_owner_date",
        "expected_inflow_realizations",
        ["owner_id", "received_date"],
        unique=False,
    )

    op.create_table(
        "expected_inflow_realization_allocations",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("realization_id", sa.Integer(), nullable=False),
        sa.Column("expected_inflow_id", sa.Integer(), nullable=False),
        sa.Column("amount", sa.BigInteger(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint(
            "amount > 0",
            name="ck_expected_inflow_realization_allocations_amount_positive",
        ),
        sa.ForeignKeyConstraint(
            ["expected_inflow_id"],
            ["expected_incomes.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["realization_id"],
            ["expected_inflow_realizations.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "realization_id",
            "expected_inflow_id",
            name="uq_expected_inflow_realization_allocation",
        ),
    )
    op.create_index(
        op.f("ix_expected_inflow_realization_allocations_id"),
        "expected_inflow_realization_allocations",
        ["id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_expected_inflow_realization_allocations_realization_id"),
        "expected_inflow_realization_allocations",
        ["realization_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_expected_inflow_realization_allocations_expected_inflow_id"),
        "expected_inflow_realization_allocations",
        ["expected_inflow_id"],
        unique=False,
    )

    op.create_table(
        "expected_inflow_realization_events",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("realization_id", sa.Integer(), nullable=False),
        sa.Column("financial_event_id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(
            ["financial_event_id"],
            ["financial_events.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["realization_id"],
            ["expected_inflow_realizations.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "realization_id",
            "financial_event_id",
            name="uq_expected_inflow_realization_event",
        ),
    )
    op.create_index(
        op.f("ix_expected_inflow_realization_events_id"),
        "expected_inflow_realization_events",
        ["id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_expected_inflow_realization_events_realization_id"),
        "expected_inflow_realization_events",
        ["realization_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_expected_inflow_realization_events_financial_event_id"),
        "expected_inflow_realization_events",
        ["financial_event_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_expected_inflow_realization_events_financial_event_id"),
        table_name="expected_inflow_realization_events",
    )
    op.drop_index(
        op.f("ix_expected_inflow_realization_events_realization_id"),
        table_name="expected_inflow_realization_events",
    )
    op.drop_index(
        op.f("ix_expected_inflow_realization_events_id"),
        table_name="expected_inflow_realization_events",
    )
    op.drop_table("expected_inflow_realization_events")

    op.drop_index(
        op.f("ix_expected_inflow_realization_allocations_expected_inflow_id"),
        table_name="expected_inflow_realization_allocations",
    )
    op.drop_index(
        op.f("ix_expected_inflow_realization_allocations_realization_id"),
        table_name="expected_inflow_realization_allocations",
    )
    op.drop_index(
        op.f("ix_expected_inflow_realization_allocations_id"),
        table_name="expected_inflow_realization_allocations",
    )
    op.drop_table("expected_inflow_realization_allocations")

    op.drop_index(
        "ix_expected_inflow_realizations_owner_date",
        table_name="expected_inflow_realizations",
    )
    op.drop_index(
        op.f("ix_expected_inflow_realizations_owner_id"),
        table_name="expected_inflow_realizations",
    )
    op.drop_index(
        op.f("ix_expected_inflow_realizations_id"),
        table_name="expected_inflow_realizations",
    )
    op.drop_table("expected_inflow_realizations")

    op.drop_index("ix_expected_incomes_owner_kind_status", table_name="expected_incomes")
    op.drop_index(op.f("ix_expected_incomes_parent_id"), table_name="expected_incomes")
    op.drop_index(op.f("ix_expected_incomes_refund_event_id"), table_name="expected_incomes")
    op.drop_index(op.f("ix_expected_incomes_asset_id"), table_name="expected_incomes")
    op.drop_index(op.f("ix_expected_incomes_kind"), table_name="expected_incomes")
    op.drop_constraint("ck_expected_incomes_exactly_one_source", "expected_incomes", type_="check")
    op.drop_constraint(
        "fk_expected_incomes_parent_id_expected_incomes",
        "expected_incomes",
        type_="foreignkey",
    )
    op.drop_constraint(
        "fk_expected_incomes_refund_event_id_financial_events",
        "expected_incomes",
        type_="foreignkey",
    )
    op.drop_constraint(
        "fk_expected_incomes_asset_id_assets",
        "expected_incomes",
        type_="foreignkey",
    )
    op.drop_column("expected_incomes", "closed_at")
    op.drop_column("expected_incomes", "close_reason")
    op.drop_column("expected_incomes", "backing_eligible")
    op.drop_column("expected_incomes", "parent_id")
    op.drop_column("expected_incomes", "refund_event_id")
    op.drop_column("expected_incomes", "asset_id")
    op.drop_column("expected_incomes", "kind")

    # PostgreSQL enum values are intentionally retained on downgrade because
    # removing enum labels requires rebuilding the type and risks legacy data.
