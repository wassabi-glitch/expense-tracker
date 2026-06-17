"""add installment event references

Revision ID: c6f9a2e8b431
Revises: b7e1c2d4f9aa
Create Date: 2026-05-19 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "c6f9a2e8b431"
down_revision: Union[str, Sequence[str], None] = "b7e1c2d4f9aa"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("financial_events", sa.Column("reference_type", sa.String(length=50), nullable=True))
    op.create_index(op.f("ix_financial_events_reference_type"), "financial_events", ["reference_type"], unique=False)

    op.add_column("entity_ledger", sa.Column("installment_plan_id", sa.Integer(), nullable=True))
    op.add_column("entity_ledger", sa.Column("installment_payment_id", sa.Integer(), nullable=True))
    op.create_index(op.f("ix_entity_ledger_installment_plan_id"), "entity_ledger", ["installment_plan_id"], unique=False)
    op.create_index(op.f("ix_entity_ledger_installment_payment_id"), "entity_ledger", ["installment_payment_id"], unique=False)
    op.create_foreign_key(
        "fk_entity_ledger_installment_plan_id",
        "entity_ledger",
        "installment_plans",
        ["installment_plan_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_foreign_key(
        "fk_entity_ledger_installment_payment_id",
        "entity_ledger",
        "installment_payments",
        ["installment_payment_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint("fk_entity_ledger_installment_payment_id", "entity_ledger", type_="foreignkey")
    op.drop_constraint("fk_entity_ledger_installment_plan_id", "entity_ledger", type_="foreignkey")
    op.drop_index(op.f("ix_entity_ledger_installment_payment_id"), table_name="entity_ledger")
    op.drop_index(op.f("ix_entity_ledger_installment_plan_id"), table_name="entity_ledger")
    op.drop_column("entity_ledger", "installment_payment_id")
    op.drop_column("entity_ledger", "installment_plan_id")

    op.drop_index(op.f("ix_financial_events_reference_type"), table_name="financial_events")
    op.drop_column("financial_events", "reference_type")
