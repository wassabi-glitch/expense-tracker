"""add payment plan type and schedule fields

Revision ID: f6a7b8c9d0e1
Revises: e1c2d3f4a5b6
Create Date: 2026-06-01 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "f6a7b8c9d0e1"
down_revision: Union[str, Sequence[str], None] = "e1c2d3f4a5b6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


PAYMENT_PLAN_TYPES = (
    "STORE_INSTALLMENT",
    "PRODUCT_FINANCING",
    "MORTGAGE",
    "AUTO_LOAN",
    "BANK_LOAN",
    "EDUCATION_LOAN",
    "SERVICE_CONTRACT",
    "OTHER",
)


def _new_enum(bind, name: str, values: tuple[str, ...]):
    if bind.dialect.name == "postgresql":
        enum_type = postgresql.ENUM(*values, name=name)
        enum_type.create(bind, checkfirst=True)
        return postgresql.ENUM(*values, name=name, create_type=False)
    return sa.Enum(*values, name=name)


def _drop_enum(bind, name: str) -> None:
    if bind.dialect.name == "postgresql":
        op.execute(f"DROP TYPE IF EXISTS {name}")


def _add_enum_values(bind, enum_name: str, values: tuple[str, ...]) -> None:
    if bind.dialect.name != "postgresql":
        return
    for value in values:
        op.execute(f"ALTER TYPE {enum_name} ADD VALUE IF NOT EXISTS '{value}'")


def upgrade() -> None:
    bind = op.get_bind()

    _add_enum_values(bind, "installmentfrequency", ("BIWEEKLY", "QUARTERLY"))
    payment_plan_type = _new_enum(bind, "paymentplantype", PAYMENT_PLAN_TYPES)

    op.add_column(
        "installment_plans",
        sa.Column(
            "plan_type",
            payment_plan_type,
            server_default="STORE_INSTALLMENT",
            nullable=False,
        ),
    )
    op.add_column("installment_plans", sa.Column("payment_count", sa.Integer(), nullable=True))
    op.add_column("installment_plans", sa.Column("regular_payment_amount", sa.BigInteger(), nullable=True))
    op.add_column("installment_plans", sa.Column("schedule_rule", sa.JSON(), nullable=True))

    op.execute(
        """
        UPDATE installment_plans
        SET
            payment_count = COALESCE(payment_count, months),
            regular_payment_amount = COALESCE(regular_payment_amount, monthly_payment_amount),
            schedule_rule = COALESCE(
                schedule_rule,
                json_build_object(
                    'source', 'BACKFILLED_FROM_LEGACY_COLUMNS',
                    'frequency', frequency::text,
                    'payment_count', months
                )
            )
        """
    )

    op.alter_column("installment_plans", "payment_count", nullable=False)
    op.alter_column("installment_plans", "regular_payment_amount", nullable=False)
    op.create_check_constraint(
        "ck_installments_payment_count_positive",
        "installment_plans",
        "payment_count > 0",
    )
    op.create_check_constraint(
        "ck_installments_regular_payment_amount_non_negative",
        "installment_plans",
        "regular_payment_amount >= 0",
    )
    op.create_index(
        "ix_installments_owner_plan_type",
        "installment_plans",
        ["owner_id", "plan_type"],
        unique=False,
    )


def downgrade() -> None:
    bind = op.get_bind()

    op.drop_index("ix_installments_owner_plan_type", table_name="installment_plans")
    op.drop_constraint(
        "ck_installments_regular_payment_amount_non_negative",
        "installment_plans",
        type_="check",
    )
    op.drop_constraint(
        "ck_installments_payment_count_positive",
        "installment_plans",
        type_="check",
    )
    op.drop_column("installment_plans", "schedule_rule")
    op.drop_column("installment_plans", "regular_payment_amount")
    op.drop_column("installment_plans", "payment_count")
    op.drop_column("installment_plans", "plan_type")
    _drop_enum(bind, "paymentplantype")
