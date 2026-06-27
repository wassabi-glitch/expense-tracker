"""rename installments to payment plans

Revision ID: f7a8b9c0d1e2
Revises: e547db0098d8
Create Date: 2026-06-26 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "f7a8b9c0d1e2"
down_revision: Union[str, Sequence[str], None] = "e547db0098d8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


TABLE_RENAMES = (
    ("installment_plans", "payment_plans"),
    ("installment_payments", "payment_plan_payments"),
    ("installment_payment_allocations", "payment_plan_payment_allocations"),
)

COLUMN_RENAMES = (
    ("goals", "linked_installment_plan_id", "linked_payment_plan_id"),
    ("entity_ledger", "installment_plan_id", "payment_plan_id"),
    ("entity_ledger", "installment_payment_id", "payment_plan_payment_id"),
    ("payment_plan_payment_allocations", "installment_payment_id", "payment_plan_payment_id"),
)

INDEX_RENAMES = (
    ("ix_installment_plans_id", "ix_payment_plans_id"),
    ("ix_installment_plans_owner_id", "ix_payment_plans_owner_id"),
    ("ix_installments_owner_status", "ix_payment_plans_owner_status"),
    ("ix_installments_owner_plan_type", "ix_payment_plans_owner_plan_type"),
    ("uq_installment_plans_debt_id", "uq_payment_plans_debt_id"),
    ("ix_installment_payments_id", "ix_payment_plan_payments_id"),
    ("ix_installment_payments_owner_id", "ix_payment_plan_payments_owner_id"),
    ("ix_installment_payments_plan_id", "ix_payment_plan_payments_plan_id"),
    ("ix_installment_payments_expense_id", "ix_payment_plan_payments_expense_id"),
    ("ix_installment_payments_event_id", "ix_payment_plan_payments_event_id"),
    ("ix_installment_payments_debt_charge_id", "ix_payment_plan_payments_debt_charge_id"),
    ("ix_installment_payments_debt_ledger_entry_id", "ix_payment_plan_payments_debt_ledger_entry_id"),
    ("ix_installment_payments_owner_due_date", "ix_payment_plan_payments_owner_due_date"),
    ("ix_installment_payments_plan_due_date", "ix_payment_plan_payments_plan_due_date"),
    ("ix_installment_payment_allocations_id", "ix_payment_plan_payment_allocations_id"),
    ("ix_installment_payment_allocations_owner_id", "ix_payment_plan_payment_allocations_owner_id"),
    ("ix_installment_payment_allocations_installment_payment_id", "ix_payment_plan_payment_allocations_payment_plan_payment_id"),
    ("ix_installment_payment_allocations_financial_event_id", "ix_payment_plan_payment_allocations_financial_event_id"),
    ("ix_installment_payment_allocations_debt_transaction_id", "ix_payment_plan_payment_allocations_debt_transaction_id"),
    ("ix_installment_payment_allocations_debt_ledger_entry_id", "ix_payment_plan_payment_allocations_debt_ledger_entry_id"),
    ("ix_installment_payment_allocations_wallet_id", "ix_payment_plan_payment_allocations_wallet_id"),
    ("ix_installment_payment_allocations_owner_date", "ix_payment_plan_payment_allocations_owner_date"),
    ("ix_goals_linked_installment_plan_id", "ix_goals_linked_payment_plan_id"),
    ("ix_entity_ledger_installment_plan_id", "ix_entity_ledger_payment_plan_id"),
    ("ix_entity_ledger_installment_payment_id", "ix_entity_ledger_payment_plan_payment_id"),
)

CONSTRAINT_RENAMES = (
    ("ck_installments_total_price_positive", "ck_payment_plans_total_price_positive"),
    ("ck_installments_down_payment_non_negative", "ck_payment_plans_down_payment_non_negative"),
    ("ck_installments_remaining_amount_non_negative", "ck_payment_plans_remaining_amount_non_negative"),
    ("ck_installments_months_positive", "ck_payment_plans_months_positive"),
    ("ck_installments_payment_count_positive", "ck_payment_plans_payment_count_positive"),
    ("ck_installments_regular_payment_amount_non_negative", "ck_payment_plans_regular_payment_amount_non_negative"),
    ("fk_installment_plans_debt_id", "fk_payment_plans_debt_id"),
    ("fk_installment_plans_expense_subcategory_id", "fk_payment_plans_expense_subcategory_id"),
    ("fk_installment_plans_project_id", "fk_payment_plans_project_id"),
    ("fk_installment_plans_project_subcategory_id", "fk_payment_plans_project_subcategory_id"),
    ("fk_installment_plans_asset_id", "fk_payment_plans_asset_id"),
    ("ck_installment_payments_amount_positive", "ck_payment_plan_payments_amount_positive"),
    ("ck_installment_payments_paid_amount_non_negative", "ck_payment_plan_payments_paid_amount_non_negative"),
    ("ck_installment_payments_written_off_amount_non_negative", "ck_payment_plan_payments_written_off_amount_non_negative"),
    ("ck_installment_payments_paid_amount_not_above_amount", "ck_payment_plan_payments_paid_amount_not_above_amount"),
    ("ck_installment_payments_settled_amount_not_above_amount", "ck_payment_plan_payments_settled_amount_not_above_amount"),
    ("fk_installment_payments_debt_charge_id", "fk_payment_plan_payments_debt_charge_id"),
    ("fk_installment_payments_debt_ledger_entry_id", "fk_payment_plan_payments_debt_ledger_entry_id"),
    ("ck_installment_payment_allocations_amount_positive", "ck_payment_plan_payment_allocations_amount_positive"),
    ("fk_entity_ledger_installment_plan_id", "fk_entity_ledger_payment_plan_id"),
    ("fk_entity_ledger_installment_payment_id", "fk_entity_ledger_payment_plan_payment_id"),
)

ENUM_TYPE_RENAMES = (
    ("installmentfrequency", "paymentplanfrequency"),
    ("installmentstatus", "paymentplanstatus"),
    ("installmentpaymentstatus", "paymentplanpaymentstatus"),
    ("installmentpaymentcomponenttype", "paymentplanpaymentcomponenttype"),
)

REFERENCE_TYPE_RENAMES = (
    ("installment_down_payment", "payment_plan_down_payment"),
    ("installment_payment", "payment_plan_payment"),
    ("installment_fee", "payment_plan_fee"),
    ("installment_penalty", "payment_plan_penalty"),
)


def _rename_index(old: str, new: str) -> None:
    op.execute(sa.text(f'ALTER INDEX IF EXISTS "{old}" RENAME TO "{new}"'))


def _rename_constraint(old: str, new: str) -> None:
    op.execute(
        sa.text(
            """
            DO $$
            DECLARE table_name text;
            BEGIN
                SELECT conrelid::regclass::text INTO table_name
                FROM pg_constraint
                WHERE conname = :old_name;

                IF table_name IS NOT NULL THEN
                    EXECUTE format(
                        'ALTER TABLE %s RENAME CONSTRAINT %I TO %I',
                        table_name,
                        :old_name,
                        :new_name
                    );
                END IF;
            END $$;
            """
        ).bindparams(old_name=old, new_name=new)
    )


def _rename_type(old: str, new: str) -> None:
    op.execute(
        sa.text(
            """
            DO $$
            BEGIN
                IF EXISTS (SELECT 1 FROM pg_type WHERE typname = :old_name)
                   AND NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = :new_name) THEN
                    EXECUTE format('ALTER TYPE %I RENAME TO %I', :old_name, :new_name);
                END IF;
            END $$;
            """
        ).bindparams(old_name=old, new_name=new)
    )


def _rename_expense_category_value(old: str, new: str) -> None:
    op.execute(
        sa.text(
            """
            DO $$
            BEGIN
                IF EXISTS (
                    SELECT 1
                    FROM pg_enum e
                    JOIN pg_type t ON t.oid = e.enumtypid
                    WHERE t.typname = 'expensecategory'
                      AND e.enumlabel = :old_value
                )
                AND NOT EXISTS (
                    SELECT 1
                    FROM pg_enum e
                    JOIN pg_type t ON t.oid = e.enumtypid
                    WHERE t.typname = 'expensecategory'
                      AND e.enumlabel = :new_value
                ) THEN
                    EXECUTE format(
                        'ALTER TYPE expensecategory RENAME VALUE %L TO %L',
                        :old_value,
                        :new_value
                    );
                END IF;
            END $$;
            """
        ).bindparams(old_value=old, new_value=new)
    )


def _column_exists(table: str, column: str) -> bool:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    return any(item["name"] == column for item in inspector.get_columns(table))


def _rename_all_forward() -> None:
    for old, new in ENUM_TYPE_RENAMES:
        _rename_type(old, new)
    _rename_expense_category_value("INSTALLMENTS_DEBT", "PAYMENT_PLANS_DEBT")

    for old, new in TABLE_RENAMES:
        op.rename_table(old, new)

    for table, old, new in COLUMN_RENAMES:
        op.alter_column(table, old, new_column_name=new)

    for old, new in INDEX_RENAMES:
        _rename_index(old, new)

    for old, new in CONSTRAINT_RENAMES:
        _rename_constraint(old, new)


def _rename_all_backward() -> None:
    for old, new in reversed(CONSTRAINT_RENAMES):
        _rename_constraint(new, old)

    for old, new in reversed(INDEX_RENAMES):
        _rename_index(new, old)

    for table, old, new in reversed(COLUMN_RENAMES):
        op.alter_column(table, new, new_column_name=old)

    for old, new in reversed(TABLE_RENAMES):
        op.rename_table(new, old)

    _rename_expense_category_value("PAYMENT_PLANS_DEBT", "INSTALLMENTS_DEBT")
    for old, new in reversed(ENUM_TYPE_RENAMES):
        _rename_type(new, old)


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        _rename_all_forward()
    else:
        for old, new in TABLE_RENAMES:
            op.rename_table(old, new)
        for table, old, new in COLUMN_RENAMES:
            with op.batch_alter_table(table) as batch_op:
                batch_op.alter_column(old, new_column_name=new)

    for old, new in REFERENCE_TYPE_RENAMES:
        op.execute(
            sa.text(
                "UPDATE financial_events SET reference_type = :new WHERE reference_type = :old"
            ).bindparams(old=old, new=new)
        )
    if _column_exists("financial_events", "outflow_type"):
        op.execute(
            sa.text(
                "UPDATE financial_events SET outflow_type = :new WHERE outflow_type = :old"
            ).bindparams(old="installment_payment", new="payment_plan_payment")
        )
    op.execute(
        sa.text(
            "UPDATE debt_ledger_entries SET event_subtype = :new WHERE event_subtype = :old"
        ).bindparams(old="INSTALLMENT_WRITE_OFF", new="PAYMENT_PLAN_WRITE_OFF")
    )


def downgrade() -> None:
    op.execute(
        sa.text(
            "UPDATE debt_ledger_entries SET event_subtype = :old WHERE event_subtype = :new"
        ).bindparams(old="INSTALLMENT_WRITE_OFF", new="PAYMENT_PLAN_WRITE_OFF")
    )
    if _column_exists("financial_events", "outflow_type"):
        op.execute(
            sa.text(
                "UPDATE financial_events SET outflow_type = :old WHERE outflow_type = :new"
            ).bindparams(old="installment_payment", new="payment_plan_payment")
        )
    for old, new in reversed(REFERENCE_TYPE_RENAMES):
        op.execute(
            sa.text(
                "UPDATE financial_events SET reference_type = :old WHERE reference_type = :new"
            ).bindparams(old=old, new=new)
        )

    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        _rename_all_backward()
    else:
        for table, old, new in reversed(COLUMN_RENAMES):
            with op.batch_alter_table(table) as batch_op:
                batch_op.alter_column(new, new_column_name=old)
        for old, new in reversed(TABLE_RENAMES):
            op.rename_table(new, old)
