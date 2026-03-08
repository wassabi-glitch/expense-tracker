"""add_auto_created_to_budgets

Revision ID: 4f52c8c3398a
Revises: ae7918f21932
Create Date: 2026-03-08 13:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "4f52c8c3398a"
down_revision: Union[str, Sequence[str], None] = "ae7918f21932"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "budgets",
        sa.Column("auto_created", sa.Boolean(), nullable=False, server_default=sa.false()),
    )


def downgrade() -> None:
    op.drop_column("budgets", "auto_created")
