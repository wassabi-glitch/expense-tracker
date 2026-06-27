"""enforce debt and payment plan date boundaries

Revision ID: f9c0d1e2f3a4
Revises: f8b9c0d1e2f3
Create Date: 2026-06-26 00:10:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "f9c0d1e2f3a4"
down_revision: Union[str, Sequence[str], None] = "f8b9c0d1e2f3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


MIN_DATE = "2020-01-01"


def _date_literal() -> str:
    if op.get_bind().dialect.name == "postgresql":
        return f"DATE '{MIN_DATE}'"
    return f"'{MIN_DATE}'"


def upgrade() -> None:
    min_date = _date_literal()

    op.execute(sa.text(f"UPDATE debts SET date = {min_date} WHERE date < {min_date}"))
    op.execute(sa.text("UPDATE debts SET expected_return_date = date WHERE expected_return_date IS NULL"))
    op.execute(sa.text(f"UPDATE debts SET expected_return_date = {min_date} WHERE expected_return_date < {min_date}"))
    op.execute(sa.text("UPDATE debts SET expected_return_date = date WHERE expected_return_date < date"))

    op.execute(sa.text(f"UPDATE payment_plans SET start_date = {min_date} WHERE start_date < {min_date}"))
    op.execute(sa.text(f"UPDATE payment_plan_payments SET due_date = {min_date} WHERE due_date < {min_date}"))

    op.alter_column(
        "debts",
        "expected_return_date",
        existing_type=sa.Date(),
        nullable=False,
    )

    op.create_check_constraint(
        "ck_debts_date_min_2020_01_01",
        "debts",
        "date >= '2020-01-01'",
    )
    op.create_check_constraint(
        "ck_debts_expected_return_date_min_2020_01_01",
        "debts",
        "expected_return_date >= '2020-01-01'",
    )
    op.create_check_constraint(
        "ck_debts_expected_return_date_not_before_date",
        "debts",
        "expected_return_date >= date",
    )
    op.create_check_constraint(
        "ck_payment_plans_start_date_min_2020_01_01",
        "payment_plans",
        "start_date >= '2020-01-01'",
    )
    op.create_check_constraint(
        "ck_payment_plan_payments_due_date_min_2020_01_01",
        "payment_plan_payments",
        "due_date >= '2020-01-01'",
    )


def downgrade() -> None:
    op.drop_constraint("ck_payment_plan_payments_due_date_min_2020_01_01", "payment_plan_payments", type_="check")
    op.drop_constraint("ck_payment_plans_start_date_min_2020_01_01", "payment_plans", type_="check")
    op.drop_constraint("ck_debts_expected_return_date_not_before_date", "debts", type_="check")
    op.drop_constraint("ck_debts_expected_return_date_min_2020_01_01", "debts", type_="check")
    op.drop_constraint("ck_debts_date_min_2020_01_01", "debts", type_="check")
    op.alter_column(
        "debts",
        "expected_return_date",
        existing_type=sa.Date(),
        nullable=True,
    )
