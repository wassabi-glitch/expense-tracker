"""add_debt_ledger_entries

Revision ID: c3d4e5f6a7b8
Revises: b1c2d3e4f5a6
Create Date: 2026-05-25 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "c3d4e5f6a7b8"
down_revision: Union[str, Sequence[str], None] = "b1c2d3e4f5a6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


ENTRY_TYPES = (
    "INITIAL",
    "CHARGE",
    "PAYMENT",
    "FORGIVENESS",
    "ADJUSTMENT",
    "REVERSAL",
    "ASSET_SETTLEMENT",
)


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        debt_ledger_entry_type = postgresql.ENUM(*ENTRY_TYPES, name="debtledgerentrytype")
        debt_ledger_entry_type.create(bind, checkfirst=True)
        entry_type = postgresql.ENUM(*ENTRY_TYPES, name="debtledgerentrytype", create_type=False)
    else:
        entry_type = sa.Enum(*ENTRY_TYPES, name="debtledgerentrytype")

    op.create_table(
        "debt_ledger_entries",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("owner_id", sa.Integer(), nullable=False),
        sa.Column("debt_id", sa.Integer(), nullable=False),
        sa.Column("financial_event_id", sa.Integer(), nullable=True),
        sa.Column("source_debt_transaction_id", sa.Integer(), nullable=True),
        sa.Column("source_debt_charge_id", sa.Integer(), nullable=True),
        sa.Column("reverses_entry_id", sa.Integer(), nullable=True),
        sa.Column("wallet_id", sa.Integer(), nullable=True),
        sa.Column("asset_id", sa.Integer(), nullable=True),
        sa.Column("entry_type", entry_type, nullable=False),
        sa.Column("amount_delta", sa.BigInteger(), nullable=False),
        sa.Column("principal_delta", sa.BigInteger(), server_default="0", nullable=False),
        sa.Column("charge_delta", sa.BigInteger(), server_default="0", nullable=False),
        sa.Column("status", sa.String(length=20), server_default="POSTED", nullable=False),
        sa.Column("entry_date", sa.Date(), nullable=False),
        sa.Column("note", sa.String(length=500), nullable=True),
        sa.Column("extra_data", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("amount_delta != 0", name="ck_debt_ledger_amount_delta_non_zero"),
        sa.ForeignKeyConstraint(["asset_id"], ["assets.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["debt_id"], ["debts.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["financial_event_id"], ["financial_events.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["reverses_entry_id"], ["debt_ledger_entries.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["source_debt_charge_id"], ["debt_charges.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["source_debt_transaction_id"], ["debt_transactions.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["wallet_id"], ["wallets.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_debt_ledger_entries_id"), "debt_ledger_entries", ["id"], unique=False)
    op.create_index(op.f("ix_debt_ledger_entries_owner_id"), "debt_ledger_entries", ["owner_id"], unique=False)
    op.create_index(op.f("ix_debt_ledger_entries_debt_id"), "debt_ledger_entries", ["debt_id"], unique=False)
    op.create_index(op.f("ix_debt_ledger_entries_financial_event_id"), "debt_ledger_entries", ["financial_event_id"], unique=False)
    op.create_index(op.f("ix_debt_ledger_entries_source_debt_transaction_id"), "debt_ledger_entries", ["source_debt_transaction_id"], unique=False)
    op.create_index(op.f("ix_debt_ledger_entries_source_debt_charge_id"), "debt_ledger_entries", ["source_debt_charge_id"], unique=False)
    op.create_index(op.f("ix_debt_ledger_entries_reverses_entry_id"), "debt_ledger_entries", ["reverses_entry_id"], unique=False)
    op.create_index(op.f("ix_debt_ledger_entries_wallet_id"), "debt_ledger_entries", ["wallet_id"], unique=False)
    op.create_index(op.f("ix_debt_ledger_entries_asset_id"), "debt_ledger_entries", ["asset_id"], unique=False)
    op.create_index("ix_debt_ledger_owner_date", "debt_ledger_entries", ["owner_id", "entry_date"], unique=False)
    op.create_index("ix_debt_ledger_debt_date", "debt_ledger_entries", ["debt_id", "entry_date"], unique=False)
    op.create_index("ix_debt_ledger_financial_event_id", "debt_ledger_entries", ["financial_event_id"], unique=False)
    op.create_index("ix_debt_ledger_source_transaction_id", "debt_ledger_entries", ["source_debt_transaction_id"], unique=False)
    op.create_index("ix_debt_ledger_source_charge_id", "debt_ledger_entries", ["source_debt_charge_id"], unique=False)

    op.execute(
        """
        INSERT INTO debt_ledger_entries (
            owner_id, debt_id, financial_event_id, wallet_id, entry_type,
            amount_delta, principal_delta, charge_delta, entry_date, note, created_at
        )
        SELECT
            owner_id, id, linked_event_id, initial_wallet_id, 'INITIAL',
            initial_amount, initial_amount, 0, date,
            'Backfilled initial debt amount', created_at
        FROM debts
        WHERE initial_amount > 0
        """
    )

    op.execute(
        """
        INSERT INTO debt_ledger_entries (
            owner_id, debt_id, source_debt_charge_id, entry_type,
            amount_delta, principal_delta, charge_delta, entry_date, note, created_at
        )
        SELECT
            owner_id, debt_id, id, 'CHARGE',
            amount, 0, amount, date, reason, created_at
        FROM debt_charges
        WHERE amount > 0
        """
    )

    op.execute(
        """
        INSERT INTO debt_ledger_entries (
            owner_id, debt_id, source_debt_transaction_id, wallet_id, entry_type,
            amount_delta, principal_delta, charge_delta, entry_date, note, created_at
        )
        SELECT
            owner_id, debt_id, id, wallet_id, 'PAYMENT',
            -amount, -amount, 0, date, note, created_at
        FROM debt_transactions
        WHERE amount > 0
        """
    )

    op.execute(
        """
        INSERT INTO debt_ledger_entries (
            owner_id, debt_id, entry_type, amount_delta, principal_delta,
            charge_delta, entry_date, note, created_at
        )
        SELECT
            owner_id, id, 'FORGIVENESS', -remaining_amount, -remaining_amount,
            0, COALESCE(updated_at::date, date), 'Backfilled forgiven debt closure', updated_at
        FROM debts
        WHERE status::text = 'FORGIVEN'
          AND remaining_amount > 0
        """
    )


def downgrade() -> None:
    op.drop_index("ix_debt_ledger_source_charge_id", table_name="debt_ledger_entries")
    op.drop_index("ix_debt_ledger_source_transaction_id", table_name="debt_ledger_entries")
    op.drop_index("ix_debt_ledger_financial_event_id", table_name="debt_ledger_entries")
    op.drop_index("ix_debt_ledger_debt_date", table_name="debt_ledger_entries")
    op.drop_index("ix_debt_ledger_owner_date", table_name="debt_ledger_entries")
    op.drop_index(op.f("ix_debt_ledger_entries_asset_id"), table_name="debt_ledger_entries")
    op.drop_index(op.f("ix_debt_ledger_entries_wallet_id"), table_name="debt_ledger_entries")
    op.drop_index(op.f("ix_debt_ledger_entries_reverses_entry_id"), table_name="debt_ledger_entries")
    op.drop_index(op.f("ix_debt_ledger_entries_source_debt_charge_id"), table_name="debt_ledger_entries")
    op.drop_index(op.f("ix_debt_ledger_entries_source_debt_transaction_id"), table_name="debt_ledger_entries")
    op.drop_index(op.f("ix_debt_ledger_entries_financial_event_id"), table_name="debt_ledger_entries")
    op.drop_index(op.f("ix_debt_ledger_entries_debt_id"), table_name="debt_ledger_entries")
    op.drop_index(op.f("ix_debt_ledger_entries_owner_id"), table_name="debt_ledger_entries")
    op.drop_index(op.f("ix_debt_ledger_entries_id"), table_name="debt_ledger_entries")
    op.drop_table("debt_ledger_entries")

    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.execute("DROP TYPE IF EXISTS debtledgerentrytype")
