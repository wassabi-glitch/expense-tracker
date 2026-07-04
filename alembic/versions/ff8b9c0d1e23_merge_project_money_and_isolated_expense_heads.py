"""finalize isolated expense migration head

Revision ID: ff8b9c0d1e23
Revises: fe7a8b9c0d12
Create Date: 2026-07-04 00:00:00.000000

"""
from typing import Sequence, Union


# revision identifiers, used by Alembic.
revision: str = "ff8b9c0d1e23"
down_revision: Union[str, Sequence[str], None] = "fe7a8b9c0d12"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
