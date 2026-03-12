"""shrink income source and note lengths

Revision ID: e2b1d5f9aa32
Revises: d3a6f5e2b1c9
Create Date: 2026-03-10 23:20:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "e2b1d5f9aa32"
down_revision: Union[str, Sequence[str], None] = "d3a6f5e2b1c9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Trim existing data first to avoid ALTER failure when shrinking VARCHAR length.
    op.execute("UPDATE income_sources SET name = LEFT(name, 32) WHERE char_length(name) > 32")
    op.execute("UPDATE income_entries SET note = LEFT(note, 200) WHERE note IS NOT NULL AND char_length(note) > 200")

    op.alter_column(
        "income_sources",
        "name",
        existing_type=sa.String(length=64),
        type_=sa.String(length=32),
        existing_nullable=False,
    )
    op.alter_column(
        "income_entries",
        "note",
        existing_type=sa.String(length=500),
        type_=sa.String(length=200),
        existing_nullable=True,
    )


def downgrade() -> None:
    op.alter_column(
        "income_entries",
        "note",
        existing_type=sa.String(length=200),
        type_=sa.String(length=500),
        existing_nullable=True,
    )
    op.alter_column(
        "income_sources",
        "name",
        existing_type=sa.String(length=32),
        type_=sa.String(length=64),
        existing_nullable=False,
    )
