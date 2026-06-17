"""obligation refactor schema

Revision ID: e1c2d3f4a5b6
Revises: d4e5f6a7b8c9
Create Date: 2026-05-31 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "e1c2d3f4a5b6"
down_revision: Union[str, Sequence[str], None] = "d4e5f6a7b8c9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


DEBT_STATUS_ADDITIONS = (
    "OVERDUE",
    "DEFAULTED",
    "IN_COLLECTION",
    "SETTLED",
    "WRITTEN_OFF",
)

INSTALLMENT_PAYMENT_STATUS_ADDITIONS = ("PARTIAL",)

DEBT_ORIGIN_KINDS = (
    "CASH_BORROWED",
    "CASH_LENT",
    "DEFERRED_EXPENSE",
    "SPLIT_REIMBURSEMENT",
    "PERSONAL_REIMBURSEMENT",
    "RECEIVABLE_INCOME",
    "FINANCED_ASSET_PURCHASE",
    "IMPORTED_BALANCE",
)

DEBT_COUNTERPARTY_KINDS = (
    "PERSON",
    "BANK",
    "COMPANY",
    "STORE",
    "GOVERNMENT",
    "OTHER",
)

DEBT_PRODUCT_KINDS = (
    "INFORMAL_DEBT",
    "BANK_LOAN",
    "CAR_LOAN",
    "MORTGAGE",
    "STORE_INSTALLMENT",
    "SERVICE_PAY_LATER",
    "PERSONAL_REIMBURSEMENT",
    "CLIENT_RECEIVABLE",
    "OTHER",
)

DEBT_LEDGER_ENTRY_SOURCES = (
    "USER",
    "SYSTEM",
    "IMPORT",
)

DEBT_ASSET_SETTLEMENT_TYPES = (
    "ASSET_RECEIVED",
    "ASSET_GIVEN",
    "COLLATERAL_TAKEN",
)

DEBT_ACTION_KINDS = (
    "RECORD_PAYMENT",
    "ADD_CHARGE",
    "FORGIVE_PARTIAL",
    "FORGIVE_FULL",
    "ADJUST_BALANCE",
    "REVERSE_ENTRY",
    "SETTLE",
    "ARCHIVE",
    "RESTORE",
    "LINK_ASSET",
    "SET_COLLATERAL",
    "RESTRUCTURE_TERMS",
)

DEBT_ACTION_RESTRICTION_LEVELS = (
    "BLOCKED",
    "REQUIRES_CONFIRMATION",
    "UNDO_UNAVAILABLE",
)

DEBT_ACTION_RESTRICTION_SOURCES = (
    "SYSTEM",
    "USER",
    "POLICY",
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
    "DEBT_CHARGES",
    "TRAVEL",
    "CHARITY",
    "ANIMALS_PETS",
)


def _new_enum(bind, name: str, values: tuple[str, ...]):
    if bind.dialect.name == "postgresql":
        enum_type = postgresql.ENUM(*values, name=name)
        enum_type.create(bind, checkfirst=True)
        return postgresql.ENUM(*values, name=name, create_type=False)
    return sa.Enum(*values, name=name)


def _existing_enum(bind, name: str, values: tuple[str, ...]):
    if bind.dialect.name == "postgresql":
        return postgresql.ENUM(*values, name=name, create_type=False)
    return sa.Enum(*values, name=name)


def _add_enum_values(bind, enum_name: str, values: tuple[str, ...]) -> None:
    if bind.dialect.name != "postgresql":
        return
    for value in values:
        op.execute(f"ALTER TYPE {enum_name} ADD VALUE IF NOT EXISTS '{value}'")


def upgrade() -> None:
    bind = op.get_bind()

    _add_enum_values(bind, "debtstatus", DEBT_STATUS_ADDITIONS)
    _add_enum_values(bind, "installmentpaymentstatus", INSTALLMENT_PAYMENT_STATUS_ADDITIONS)

    debt_origin_kind = _new_enum(bind, "debtoriginkind", DEBT_ORIGIN_KINDS)
    debt_counterparty_kind = _new_enum(bind, "debtcounterpartykind", DEBT_COUNTERPARTY_KINDS)
    debt_product_kind = _new_enum(bind, "debtproductkind", DEBT_PRODUCT_KINDS)
    debt_ledger_entry_source = _new_enum(bind, "debtledgerentrysource", DEBT_LEDGER_ENTRY_SOURCES)
    debt_asset_settlement_type = _new_enum(bind, "debtassetsettlementtype", DEBT_ASSET_SETTLEMENT_TYPES)
    debt_action_kind = _new_enum(bind, "debtactionkind", DEBT_ACTION_KINDS)
    debt_action_restriction_level = _new_enum(
        bind,
        "debtactionrestrictionlevel",
        DEBT_ACTION_RESTRICTION_LEVELS,
    )
    debt_action_restriction_source = _new_enum(
        bind,
        "debtactionrestrictionsource",
        DEBT_ACTION_RESTRICTION_SOURCES,
    )
    expense_category = _existing_enum(bind, "expensecategory", EXPENSE_CATEGORIES)

    op.add_column(
        "debts",
        sa.Column("origin_kind", debt_origin_kind, server_default="IMPORTED_BALANCE", nullable=False),
    )
    op.add_column(
        "debts",
        sa.Column("counterparty_kind", debt_counterparty_kind, server_default="OTHER", nullable=False),
    )
    op.add_column("debts", sa.Column("product_kind", debt_product_kind, nullable=True))
    op.add_column("debts", sa.Column("expense_subcategory_id", sa.Integer(), nullable=True))
    op.add_column("debts", sa.Column("project_id", sa.Integer(), nullable=True))
    op.add_column("debts", sa.Column("project_subcategory_id", sa.Integer(), nullable=True))
    op.create_foreign_key(
        "fk_debts_expense_subcategory_id",
        "debts",
        "user_subcategories",
        ["expense_subcategory_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_foreign_key(
        "fk_debts_project_id",
        "debts",
        "projects",
        ["project_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_foreign_key(
        "fk_debts_project_subcategory_id",
        "debts",
        "project_subcategories",
        ["project_subcategory_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index("ix_debts_owner_origin", "debts", ["owner_id", "origin_kind"], unique=False)
    op.create_index("ix_debts_owner_product", "debts", ["owner_id", "product_kind"], unique=False)

    if bind.dialect.name == "postgresql":
        op.execute(
            """
            UPDATE debts
            SET origin_kind = CASE
                WHEN debt_type::text = 'OWING' AND is_money_transferred IS TRUE THEN 'CASH_BORROWED'::debtoriginkind
                WHEN debt_type::text = 'OWED' AND is_money_transferred IS TRUE THEN 'CASH_LENT'::debtoriginkind
                WHEN debt_type::text = 'OWING' AND COALESCE(is_money_transferred, false) IS FALSE THEN 'DEFERRED_EXPENSE'::debtoriginkind
                WHEN debt_type::text = 'OWED' AND COALESCE(is_money_transferred, false) IS FALSE
                     AND linked_event_id IS NOT NULL AND income_source_id IS NULL THEN 'SPLIT_REIMBURSEMENT'::debtoriginkind
                WHEN debt_type::text = 'OWED' AND income_source_id IS NOT NULL THEN 'RECEIVABLE_INCOME'::debtoriginkind
                WHEN debt_type::text = 'OWED' THEN 'PERSONAL_REIMBURSEMENT'::debtoriginkind
                ELSE 'IMPORTED_BALANCE'::debtoriginkind
            END
            """
        )
        op.execute(
            """
            UPDATE debts
            SET product_kind = CASE
                WHEN origin_kind::text IN ('SPLIT_REIMBURSEMENT', 'PERSONAL_REIMBURSEMENT')
                    THEN 'PERSONAL_REIMBURSEMENT'::debtproductkind
                WHEN origin_kind::text = 'RECEIVABLE_INCOME'
                    THEN 'CLIENT_RECEIVABLE'::debtproductkind
                WHEN origin_kind::text != 'IMPORTED_BALANCE'
                    THEN 'INFORMAL_DEBT'::debtproductkind
                ELSE product_kind
            END
            WHERE product_kind IS NULL
            """
        )
        op.execute(
            """
            UPDATE debts
            SET counterparty_kind = 'PERSON'::debtcounterpartykind
            WHERE origin_kind::text IN (
                'CASH_BORROWED',
                'CASH_LENT',
                'DEFERRED_EXPENSE',
                'SPLIT_REIMBURSEMENT',
                'PERSONAL_REIMBURSEMENT'
            )
            """
        )
        op.execute(
            """
            WITH event_context AS (
                SELECT DISTINCT ON (event_id)
                    event_id,
                    category,
                    subcategory_id,
                    project_id,
                    project_subcategory_id
                FROM entity_ledger
                WHERE category IS NOT NULL
                ORDER BY event_id, id
            )
            UPDATE debts d
            SET
                expense_category = COALESCE(d.expense_category, event_context.category),
                expense_subcategory_id = COALESCE(d.expense_subcategory_id, event_context.subcategory_id),
                project_id = COALESCE(d.project_id, event_context.project_id),
                project_subcategory_id = COALESCE(d.project_subcategory_id, event_context.project_subcategory_id)
            FROM event_context
            WHERE d.linked_event_id = event_context.event_id
              AND d.origin_kind::text IN ('DEFERRED_EXPENSE', 'SPLIT_REIMBURSEMENT', 'FINANCED_ASSET_PURCHASE')
            """
        )

    op.add_column("debt_ledger_entries", sa.Column("balance_after", sa.BigInteger(), nullable=True))
    op.add_column("debt_ledger_entries", sa.Column("event_subtype", sa.String(length=50), nullable=True))
    op.add_column(
        "debt_ledger_entries",
        sa.Column("source", debt_ledger_entry_source, server_default="USER", nullable=False),
    )
    op.add_column(
        "debt_ledger_entries",
        sa.Column("is_reversible", sa.Boolean(), server_default=sa.text("true"), nullable=False),
    )
    op.execute(
        """
        WITH ordered AS (
            SELECT
                id,
                SUM(amount_delta) OVER (
                    PARTITION BY debt_id
                    ORDER BY entry_date, id
                    ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
                ) AS running_balance
            FROM debt_ledger_entries
            WHERE status = 'POSTED'
        )
        UPDATE debt_ledger_entries dle
        SET balance_after = ordered.running_balance
        FROM ordered
        WHERE dle.id = ordered.id
        """
    )
    if bind.dialect.name == "postgresql":
        op.execute(
            """
            UPDATE debt_ledger_entries
            SET event_subtype = 'FULL_FORGIVENESS'
            WHERE entry_type::text = 'FORGIVENESS'
              AND event_subtype IS NULL
            """
        )
        op.execute(
            """
            UPDATE debt_ledger_entries
            SET source = 'SYSTEM'::debtledgerentrysource
            WHERE note ILIKE 'Backfilled%'
            """
        )

    op.create_table(
        "debt_formal_details",
        sa.Column("debt_id", sa.Integer(), nullable=False),
        sa.Column("owner_id", sa.Integer(), nullable=False),
        sa.Column("institution_name", sa.String(length=100), nullable=True),
        sa.Column("contract_number", sa.String(length=100), nullable=True),
        sa.Column("linked_asset_id", sa.Integer(), nullable=True),
        sa.Column("collateral_asset_id", sa.Integer(), nullable=True),
        sa.Column("statement_balance", sa.BigInteger(), nullable=True),
        sa.Column("statement_balance_date", sa.Date(), nullable=True),
        sa.Column("next_due_date", sa.Date(), nullable=True),
        sa.Column("annual_rate_bps", sa.Integer(), nullable=True),
        sa.Column("terms_summary", sa.String(length=500), nullable=True),
        sa.Column("extra_data", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint(
            "statement_balance IS NULL OR statement_balance >= 0",
            name="ck_debt_formal_statement_balance_non_negative",
        ),
        sa.CheckConstraint(
            "annual_rate_bps IS NULL OR annual_rate_bps >= 0",
            name="ck_debt_formal_annual_rate_bps_non_negative",
        ),
        sa.ForeignKeyConstraint(["collateral_asset_id"], ["assets.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["debt_id"], ["debts.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["linked_asset_id"], ["assets.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("debt_id"),
    )
    op.create_index(op.f("ix_debt_formal_details_owner_id"), "debt_formal_details", ["owner_id"], unique=False)
    op.create_index(op.f("ix_debt_formal_details_linked_asset_id"), "debt_formal_details", ["linked_asset_id"], unique=False)
    op.create_index(op.f("ix_debt_formal_details_collateral_asset_id"), "debt_formal_details", ["collateral_asset_id"], unique=False)

    op.create_table(
        "debt_transaction_wallet_allocations",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("owner_id", sa.Integer(), nullable=False),
        sa.Column("debt_id", sa.Integer(), nullable=False),
        sa.Column("debt_transaction_id", sa.Integer(), nullable=False),
        sa.Column("wallet_id", sa.Integer(), nullable=False),
        sa.Column("amount", sa.BigInteger(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("amount > 0", name="ck_debt_transaction_wallet_allocations_amount_positive"),
        sa.ForeignKeyConstraint(["debt_id"], ["debts.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["debt_transaction_id"], ["debt_transactions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["wallet_id"], ["wallets.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("debt_transaction_id", "wallet_id", name="uq_debt_transaction_wallet_allocations_wallet"),
    )
    op.create_index(op.f("ix_debt_transaction_wallet_allocations_id"), "debt_transaction_wallet_allocations", ["id"], unique=False)
    op.create_index(op.f("ix_debt_transaction_wallet_allocations_owner_id"), "debt_transaction_wallet_allocations", ["owner_id"], unique=False)
    op.create_index(op.f("ix_debt_transaction_wallet_allocations_debt_id"), "debt_transaction_wallet_allocations", ["debt_id"], unique=False)
    op.create_index(op.f("ix_debt_transaction_wallet_allocations_debt_transaction_id"), "debt_transaction_wallet_allocations", ["debt_transaction_id"], unique=False)
    op.create_index(op.f("ix_debt_transaction_wallet_allocations_wallet_id"), "debt_transaction_wallet_allocations", ["wallet_id"], unique=False)
    op.execute(
        """
        INSERT INTO debt_transaction_wallet_allocations (
            owner_id, debt_id, debt_transaction_id, wallet_id, amount, created_at
        )
        SELECT owner_id, debt_id, id, wallet_id, amount, created_at
        FROM debt_transactions
        WHERE wallet_id IS NOT NULL
          AND amount > 0
        ON CONFLICT ON CONSTRAINT uq_debt_transaction_wallet_allocations_wallet DO NOTHING
        """
    )

    op.create_table(
        "debt_asset_settlements",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("owner_id", sa.Integer(), nullable=False),
        sa.Column("debt_id", sa.Integer(), nullable=False),
        sa.Column("asset_id", sa.Integer(), nullable=True),
        sa.Column("financial_event_id", sa.Integer(), nullable=True),
        sa.Column("debt_ledger_entry_id", sa.Integer(), nullable=True),
        sa.Column("settlement_type", debt_asset_settlement_type, nullable=False),
        sa.Column("amount", sa.BigInteger(), nullable=False),
        sa.Column("settlement_date", sa.Date(), nullable=False),
        sa.Column("note", sa.String(length=500), nullable=True),
        sa.Column("extra_data", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("amount > 0", name="ck_debt_asset_settlements_amount_positive"),
        sa.ForeignKeyConstraint(["asset_id"], ["assets.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["debt_id"], ["debts.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["debt_ledger_entry_id"], ["debt_ledger_entries.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["financial_event_id"], ["financial_events.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_debt_asset_settlements_id"), "debt_asset_settlements", ["id"], unique=False)
    op.create_index(op.f("ix_debt_asset_settlements_owner_id"), "debt_asset_settlements", ["owner_id"], unique=False)
    op.create_index(op.f("ix_debt_asset_settlements_debt_id"), "debt_asset_settlements", ["debt_id"], unique=False)
    op.create_index(op.f("ix_debt_asset_settlements_asset_id"), "debt_asset_settlements", ["asset_id"], unique=False)
    op.create_index(op.f("ix_debt_asset_settlements_financial_event_id"), "debt_asset_settlements", ["financial_event_id"], unique=False)
    op.create_index(op.f("ix_debt_asset_settlements_debt_ledger_entry_id"), "debt_asset_settlements", ["debt_ledger_entry_id"], unique=False)
    op.create_index("ix_debt_asset_settlements_debt_date", "debt_asset_settlements", ["debt_id", "settlement_date"], unique=False)

    op.create_table(
        "debt_action_restrictions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("owner_id", sa.Integer(), nullable=False),
        sa.Column("debt_id", sa.Integer(), nullable=False),
        sa.Column("action_kind", debt_action_kind, nullable=False),
        sa.Column("level", debt_action_restriction_level, nullable=False),
        sa.Column("reason_code", sa.String(length=100), nullable=False),
        sa.Column("source", debt_action_restriction_source, server_default="SYSTEM", nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("details", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["debt_id"], ["debts.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_debt_action_restrictions_id"), "debt_action_restrictions", ["id"], unique=False)
    op.create_index(op.f("ix_debt_action_restrictions_owner_id"), "debt_action_restrictions", ["owner_id"], unique=False)
    op.create_index(op.f("ix_debt_action_restrictions_debt_id"), "debt_action_restrictions", ["debt_id"], unique=False)
    op.create_index("ix_debt_action_restrictions_debt_active", "debt_action_restrictions", ["debt_id", "is_active"], unique=False)
    op.create_index("ix_debt_action_restrictions_owner_action", "debt_action_restrictions", ["owner_id", "action_kind"], unique=False)

    op.add_column("installment_plans", sa.Column("debt_id", sa.Integer(), nullable=True))
    op.add_column("installment_plans", sa.Column("expense_category", expense_category, nullable=True))
    op.add_column("installment_plans", sa.Column("expense_subcategory_id", sa.Integer(), nullable=True))
    op.add_column("installment_plans", sa.Column("project_id", sa.Integer(), nullable=True))
    op.add_column("installment_plans", sa.Column("project_subcategory_id", sa.Integer(), nullable=True))
    op.add_column("installment_plans", sa.Column("asset_id", sa.Integer(), nullable=True))
    op.create_index("uq_installment_plans_debt_id", "installment_plans", ["debt_id"], unique=True)
    op.create_foreign_key("fk_installment_plans_debt_id", "installment_plans", "debts", ["debt_id"], ["id"], ondelete="SET NULL")
    op.create_foreign_key("fk_installment_plans_expense_subcategory_id", "installment_plans", "user_subcategories", ["expense_subcategory_id"], ["id"], ondelete="SET NULL")
    op.create_foreign_key("fk_installment_plans_project_id", "installment_plans", "projects", ["project_id"], ["id"], ondelete="SET NULL")
    op.create_foreign_key("fk_installment_plans_project_subcategory_id", "installment_plans", "project_subcategories", ["project_subcategory_id"], ["id"], ondelete="SET NULL")
    op.create_foreign_key("fk_installment_plans_asset_id", "installment_plans", "assets", ["asset_id"], ["id"], ondelete="SET NULL")
    op.execute(
        """
        UPDATE installment_plans
        SET expense_category = 'INSTALLMENTS_DEBT'
        WHERE expense_category IS NULL
        """
    )

    op.add_column("installment_payments", sa.Column("paid_amount", sa.BigInteger(), server_default="0", nullable=False))
    op.add_column("installment_payments", sa.Column("debt_ledger_entry_id", sa.Integer(), nullable=True))
    op.create_check_constraint(
        "ck_installment_payments_paid_amount_non_negative",
        "installment_payments",
        "paid_amount >= 0",
    )
    op.create_check_constraint(
        "ck_installment_payments_paid_amount_not_above_amount",
        "installment_payments",
        "paid_amount <= amount",
    )
    op.create_index(op.f("ix_installment_payments_debt_ledger_entry_id"), "installment_payments", ["debt_ledger_entry_id"], unique=False)
    op.create_foreign_key(
        "fk_installment_payments_debt_ledger_entry_id",
        "installment_payments",
        "debt_ledger_entries",
        ["debt_ledger_entry_id"],
        ["id"],
        ondelete="SET NULL",
    )
    if bind.dialect.name == "postgresql":
        op.execute(
            """
            UPDATE installment_payments
            SET paid_amount = amount
            WHERE status::text = 'PAID'
            """
        )

    op.create_table(
        "installment_payment_allocations",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("owner_id", sa.Integer(), nullable=False),
        sa.Column("installment_payment_id", sa.Integer(), nullable=False),
        sa.Column("financial_event_id", sa.Integer(), nullable=True),
        sa.Column("debt_transaction_id", sa.Integer(), nullable=True),
        sa.Column("debt_ledger_entry_id", sa.Integer(), nullable=True),
        sa.Column("wallet_id", sa.Integer(), nullable=True),
        sa.Column("amount", sa.BigInteger(), nullable=False),
        sa.Column("paid_date", sa.Date(), nullable=False),
        sa.Column("note", sa.String(length=200), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("amount > 0", name="ck_installment_payment_allocations_amount_positive"),
        sa.ForeignKeyConstraint(["debt_ledger_entry_id"], ["debt_ledger_entries.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["debt_transaction_id"], ["debt_transactions.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["financial_event_id"], ["financial_events.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["installment_payment_id"], ["installment_payments.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["wallet_id"], ["wallets.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_installment_payment_allocations_id"), "installment_payment_allocations", ["id"], unique=False)
    op.create_index(op.f("ix_installment_payment_allocations_owner_id"), "installment_payment_allocations", ["owner_id"], unique=False)
    op.create_index(op.f("ix_installment_payment_allocations_installment_payment_id"), "installment_payment_allocations", ["installment_payment_id"], unique=False)
    op.create_index(op.f("ix_installment_payment_allocations_financial_event_id"), "installment_payment_allocations", ["financial_event_id"], unique=False)
    op.create_index(op.f("ix_installment_payment_allocations_debt_transaction_id"), "installment_payment_allocations", ["debt_transaction_id"], unique=False)
    op.create_index(op.f("ix_installment_payment_allocations_debt_ledger_entry_id"), "installment_payment_allocations", ["debt_ledger_entry_id"], unique=False)
    op.create_index(op.f("ix_installment_payment_allocations_wallet_id"), "installment_payment_allocations", ["wallet_id"], unique=False)
    op.create_index("ix_installment_payment_allocations_owner_date", "installment_payment_allocations", ["owner_id", "paid_date"], unique=False)
    if bind.dialect.name == "postgresql":
        op.execute(
            """
            INSERT INTO installment_payment_allocations (
                owner_id,
                installment_payment_id,
                financial_event_id,
                debt_ledger_entry_id,
                amount,
                paid_date,
                note,
                created_at
            )
            SELECT
                owner_id,
                id,
                event_id,
                debt_ledger_entry_id,
                amount,
                COALESCE(paid_date, due_date),
                note,
                created_at
            FROM installment_payments
            WHERE status::text = 'PAID'
              AND amount > 0
            """
        )


def downgrade() -> None:
    op.drop_index("ix_installment_payment_allocations_owner_date", table_name="installment_payment_allocations")
    op.drop_index(op.f("ix_installment_payment_allocations_wallet_id"), table_name="installment_payment_allocations")
    op.drop_index(op.f("ix_installment_payment_allocations_debt_ledger_entry_id"), table_name="installment_payment_allocations")
    op.drop_index(op.f("ix_installment_payment_allocations_debt_transaction_id"), table_name="installment_payment_allocations")
    op.drop_index(op.f("ix_installment_payment_allocations_financial_event_id"), table_name="installment_payment_allocations")
    op.drop_index(op.f("ix_installment_payment_allocations_installment_payment_id"), table_name="installment_payment_allocations")
    op.drop_index(op.f("ix_installment_payment_allocations_owner_id"), table_name="installment_payment_allocations")
    op.drop_index(op.f("ix_installment_payment_allocations_id"), table_name="installment_payment_allocations")
    op.drop_table("installment_payment_allocations")

    op.drop_constraint("fk_installment_payments_debt_ledger_entry_id", "installment_payments", type_="foreignkey")
    op.drop_index(op.f("ix_installment_payments_debt_ledger_entry_id"), table_name="installment_payments")
    op.drop_constraint("ck_installment_payments_paid_amount_not_above_amount", "installment_payments", type_="check")
    op.drop_constraint("ck_installment_payments_paid_amount_non_negative", "installment_payments", type_="check")
    op.drop_column("installment_payments", "debt_ledger_entry_id")
    op.drop_column("installment_payments", "paid_amount")

    op.drop_constraint("fk_installment_plans_asset_id", "installment_plans", type_="foreignkey")
    op.drop_constraint("fk_installment_plans_project_subcategory_id", "installment_plans", type_="foreignkey")
    op.drop_constraint("fk_installment_plans_project_id", "installment_plans", type_="foreignkey")
    op.drop_constraint("fk_installment_plans_expense_subcategory_id", "installment_plans", type_="foreignkey")
    op.drop_constraint("fk_installment_plans_debt_id", "installment_plans", type_="foreignkey")
    op.drop_index("uq_installment_plans_debt_id", table_name="installment_plans")
    op.drop_column("installment_plans", "asset_id")
    op.drop_column("installment_plans", "project_subcategory_id")
    op.drop_column("installment_plans", "project_id")
    op.drop_column("installment_plans", "expense_subcategory_id")
    op.drop_column("installment_plans", "expense_category")
    op.drop_column("installment_plans", "debt_id")

    op.drop_index("ix_debt_action_restrictions_owner_action", table_name="debt_action_restrictions")
    op.drop_index("ix_debt_action_restrictions_debt_active", table_name="debt_action_restrictions")
    op.drop_index(op.f("ix_debt_action_restrictions_debt_id"), table_name="debt_action_restrictions")
    op.drop_index(op.f("ix_debt_action_restrictions_owner_id"), table_name="debt_action_restrictions")
    op.drop_index(op.f("ix_debt_action_restrictions_id"), table_name="debt_action_restrictions")
    op.drop_table("debt_action_restrictions")

    op.drop_index("ix_debt_asset_settlements_debt_date", table_name="debt_asset_settlements")
    op.drop_index(op.f("ix_debt_asset_settlements_debt_ledger_entry_id"), table_name="debt_asset_settlements")
    op.drop_index(op.f("ix_debt_asset_settlements_financial_event_id"), table_name="debt_asset_settlements")
    op.drop_index(op.f("ix_debt_asset_settlements_asset_id"), table_name="debt_asset_settlements")
    op.drop_index(op.f("ix_debt_asset_settlements_debt_id"), table_name="debt_asset_settlements")
    op.drop_index(op.f("ix_debt_asset_settlements_owner_id"), table_name="debt_asset_settlements")
    op.drop_index(op.f("ix_debt_asset_settlements_id"), table_name="debt_asset_settlements")
    op.drop_table("debt_asset_settlements")

    op.drop_index(op.f("ix_debt_transaction_wallet_allocations_wallet_id"), table_name="debt_transaction_wallet_allocations")
    op.drop_index(op.f("ix_debt_transaction_wallet_allocations_debt_transaction_id"), table_name="debt_transaction_wallet_allocations")
    op.drop_index(op.f("ix_debt_transaction_wallet_allocations_debt_id"), table_name="debt_transaction_wallet_allocations")
    op.drop_index(op.f("ix_debt_transaction_wallet_allocations_owner_id"), table_name="debt_transaction_wallet_allocations")
    op.drop_index(op.f("ix_debt_transaction_wallet_allocations_id"), table_name="debt_transaction_wallet_allocations")
    op.drop_table("debt_transaction_wallet_allocations")

    op.drop_index(op.f("ix_debt_formal_details_collateral_asset_id"), table_name="debt_formal_details")
    op.drop_index(op.f("ix_debt_formal_details_linked_asset_id"), table_name="debt_formal_details")
    op.drop_index(op.f("ix_debt_formal_details_owner_id"), table_name="debt_formal_details")
    op.drop_table("debt_formal_details")

    op.drop_column("debt_ledger_entries", "is_reversible")
    op.drop_column("debt_ledger_entries", "source")
    op.drop_column("debt_ledger_entries", "event_subtype")
    op.drop_column("debt_ledger_entries", "balance_after")

    op.drop_index("ix_debts_owner_product", table_name="debts")
    op.drop_index("ix_debts_owner_origin", table_name="debts")
    op.drop_constraint("fk_debts_project_subcategory_id", "debts", type_="foreignkey")
    op.drop_constraint("fk_debts_project_id", "debts", type_="foreignkey")
    op.drop_constraint("fk_debts_expense_subcategory_id", "debts", type_="foreignkey")
    op.drop_column("debts", "project_subcategory_id")
    op.drop_column("debts", "project_id")
    op.drop_column("debts", "expense_subcategory_id")
    op.drop_column("debts", "product_kind")
    op.drop_column("debts", "counterparty_kind")
    op.drop_column("debts", "origin_kind")

    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.execute("DROP TYPE IF EXISTS debtactionrestrictionsource")
        op.execute("DROP TYPE IF EXISTS debtactionrestrictionlevel")
        op.execute("DROP TYPE IF EXISTS debtactionkind")
        op.execute("DROP TYPE IF EXISTS debtassetsettlementtype")
        op.execute("DROP TYPE IF EXISTS debtledgerentrysource")
        op.execute("DROP TYPE IF EXISTS debtproductkind")
        op.execute("DROP TYPE IF EXISTS debtcounterpartykind")
        op.execute("DROP TYPE IF EXISTS debtoriginkind")
