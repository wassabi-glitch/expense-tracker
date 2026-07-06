"""bridge local project state

Revision ID: ff8b9c0d1e23
Revises: 1a2b3c4d5e6f
Create Date: 2026-07-06 00:00:00.000000

"""
from typing import Sequence, Union


revision: str = "ff8b9c0d1e23"
down_revision: Union[str, Sequence[str], None] = "1a2b3c4d5e6f"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
