"""add_installment_payment_components

Revision ID: f4c7b9e2a130
Revises: e7b9c2d4a6f1
Create Date: 2026-06-06 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "f4c7b9e2a130"
down_revision: Union[str, Sequence[str], None] = "e7b9c2d4a6f1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


component_type_enum = sa.Enum(
    "PRINCIPAL",
    "CHARGE",
    name="installmentpaymentcomponenttype",
)


def upgrade() -> None:
    bind = op.get_bind()
    component_type_enum.create(bind, checkfirst=True)

    op.add_column(
        "installment_payments",
        sa.Column("debt_charge_id", sa.Integer(), nullable=True),
    )
    op.add_column(
        "installment_payments",
        sa.Column("written_off_amount", sa.BigInteger(), server_default="0", nullable=False),
    )
    op.add_column(
        "installment_payments",
        sa.Column(
            "component_type",
            component_type_enum,
            server_default="PRINCIPAL",
            nullable=False,
        ),
    )
    op.create_index(
        op.f("ix_installment_payments_debt_charge_id"),
        "installment_payments",
        ["debt_charge_id"],
        unique=False,
    )
    op.create_foreign_key(
        "fk_installment_payments_debt_charge_id",
        "installment_payments",
        "debt_charges",
        ["debt_charge_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_check_constraint(
        "ck_installment_payments_written_off_amount_non_negative",
        "installment_payments",
        "written_off_amount >= 0",
    )
    op.create_check_constraint(
        "ck_installment_payments_settled_amount_not_above_amount",
        "installment_payments",
        "paid_amount + written_off_amount <= amount",
    )

    op.execute(
        """
        UPDATE installment_payments p
        SET written_off_amount = p.amount - p.paid_amount
        FROM debt_ledger_entries e
        WHERE p.debt_ledger_entry_id = e.id
          AND p.status = 'PAID'
          AND p.paid_amount < p.amount
          AND e.entry_type = 'ADJUSTMENT'
          AND COALESCE(e.note, '') LIKE 'Write-off for installment payment%'
        """
    )

    op.execute(
        """
        UPDATE installment_payments p
        SET component_type = 'CHARGE',
            debt_charge_id = c.id
        FROM installment_plans pl, debt_charges c
        WHERE p.plan_id = pl.id
          AND pl.debt_id = c.debt_id
          AND p.amount = c.amount
          AND p.due_date = c.date
          AND p.note IS NOT NULL
          AND c.reason IS NOT NULL
          AND p.note = c.reason
        """
    )


def downgrade() -> None:
    op.drop_constraint("ck_installment_payments_settled_amount_not_above_amount", "installment_payments", type_="check")
    op.drop_constraint("ck_installment_payments_written_off_amount_non_negative", "installment_payments", type_="check")
    op.drop_constraint("fk_installment_payments_debt_charge_id", "installment_payments", type_="foreignkey")
    op.drop_index(op.f("ix_installment_payments_debt_charge_id"), table_name="installment_payments")
    op.drop_column("installment_payments", "component_type")
    op.drop_column("installment_payments", "written_off_amount")
    op.drop_column("installment_payments", "debt_charge_id")

    bind = op.get_bind()
    component_type_enum.drop(bind, checkfirst=True)
