"""add_payment_plan_schedule_model_and_installment_grouping

Revision ID: 7823c887d5fd
Revises: 4ce26c366899
Create Date: 2026-07-10 14:13:06.418641

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '7823c887d5fd'
down_revision: Union[str, Sequence[str], None] = '4ce26c366899'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Add schedule_model enum type
    schedule_model_enum = sa.Enum(
        "FLAT_TOTAL",
        "AMORTIZED_LOAN",
        "MANUAL_CONTRACT_SCHEDULE",
        name="schemodel",
    )
    schedule_model_enum.create(op.get_bind(), checkfirst=True)

    # Add schedule_model column to payment_plans
    op.add_column(
        "payment_plans",
        sa.Column(
            "schedule_model",
            schedule_model_enum,
            nullable=False,
            server_default="FLAT_TOTAL",
        ),
    )

    # Add generation_metadata column to payment_plans
    op.add_column(
        "payment_plans",
        sa.Column(
            "generation_metadata",
            sa.JSON(),
            nullable=True,
        ),
    )

    # Add installment_number column to payment_plan_payments
    op.add_column(
        "payment_plan_payments",
        sa.Column(
            "installment_number",
            sa.Integer(),
            nullable=True,
        ),
    )


def downgrade() -> None:
    """Downgrade schema."""
    # Remove installment_number from payment_plan_payments
    op.drop_column("payment_plan_payments", "installment_number")

    # Remove generation_metadata from payment_plans
    op.drop_column("payment_plans", "generation_metadata")

    # Remove schedule_model column from payment_plans
    op.drop_column("payment_plans", "schedule_model")

    # Drop the enum type
    sa.Enum(
        "FLAT_TOTAL",
        "AMORTIZED_LOAN",
        "MANUAL_CONTRACT_SCHEDULE",
        name="schemodel",
    ).drop(op.get_bind(), checkfirst=True)
