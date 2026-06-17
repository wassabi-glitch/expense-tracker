"""add recurring projection horizons

Revision ID: 4b8f0d6e2a91
Revises: 6b7c8d9e0f12
Create Date: 2026-06-14
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "4b8f0d6e2a91"
down_revision: Union[str, Sequence[str], None] = "6b7c8d9e0f12"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "recurring_expenses",
        sa.Column("custom_projection_horizons", sa.JSON(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("recurring_expenses", "custom_projection_horizons")
