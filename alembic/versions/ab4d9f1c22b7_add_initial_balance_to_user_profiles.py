"""add initial balance to user profiles

Revision ID: ab4d9f1c22b7
Revises: e2b1d5f9aa32
Create Date: 2026-03-11 10:15:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "ab4d9f1c22b7"
down_revision: Union[str, Sequence[str], None] = "e2b1d5f9aa32"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "user_profiles",
        sa.Column("initial_balance", sa.BigInteger(), nullable=False, server_default="0"),
    )
    op.create_check_constraint(
        "ck_user_profiles_initial_balance_non_negative",
        "user_profiles",
        "initial_balance >= 0",
    )
    op.alter_column("user_profiles", "initial_balance", server_default=None)


def downgrade() -> None:
    op.drop_constraint(
        "ck_user_profiles_initial_balance_non_negative",
        "user_profiles",
        type_="check",
    )
    op.drop_column("user_profiles", "initial_balance")
