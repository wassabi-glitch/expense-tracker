"""add expense min date check

Revision ID: 61c6fc5a5fc6
Revises: 0bd680935b0f
Create Date: 2026-02-26 06:32:02.733197

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = '61c6fc5a5fc6'
down_revision: Union[str, Sequence[str], None] = '0bd680935b0f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_check_constraint(
        "ck_expenses_date_min_2020_01_01",
        "expenses",
        "date >= DATE '2020-01-01'",
    )


def downgrade() -> None:
    op.drop_constraint(
        "ck_expenses_date_min_2020_01_01",
        "expenses",
        type_="check",
    )
