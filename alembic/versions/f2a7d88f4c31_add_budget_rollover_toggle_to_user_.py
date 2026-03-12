"""add budget rollover toggle to user profiles

Revision ID: f2a7d88f4c31
Revises: e5c1d9a7b442
Create Date: 2026-03-12 23:59:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "f2a7d88f4c31"
down_revision: Union[str, Sequence[str], None] = "e5c1d9a7b442"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "user_profiles",
        sa.Column(
            "budget_rollover_enabled",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
        ),
    )
    op.alter_column("user_profiles", "budget_rollover_enabled", server_default=None)


def downgrade() -> None:
    op.drop_column("user_profiles", "budget_rollover_enabled")
