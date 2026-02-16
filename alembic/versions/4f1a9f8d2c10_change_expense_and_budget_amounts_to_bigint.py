"""change expense and budget amounts to bigint

Revision ID: 4f1a9f8d2c10
Revises: 7876c365926e
Create Date: 2026-02-05 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "4f1a9f8d2c10"
down_revision: Union[str, Sequence[str], None] = "7876c365926e"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column(
        "expenses",
        "amount",
        existing_type=sa.Float(),
        type_=sa.BigInteger(),
        postgresql_using="ROUND(amount)::bigint",
        existing_nullable=False,
    )
    op.alter_column(
        "budgets",
        "monthly_limit",
        existing_type=sa.Float(),
        type_=sa.BigInteger(),
        postgresql_using="ROUND(monthly_limit)::bigint",
        existing_nullable=False,
    )


def downgrade() -> None:
    op.alter_column(
        "budgets",
        "monthly_limit",
        existing_type=sa.BigInteger(),
        type_=sa.Float(),
        postgresql_using="monthly_limit::double precision",
        existing_nullable=False,
    )
    op.alter_column(
        "expenses",
        "amount",
        existing_type=sa.BigInteger(),
        type_=sa.Float(),
        postgresql_using="amount::double precision",
        existing_nullable=False,
    )
