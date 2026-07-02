"""add project target estimate

Revision ID: e3f4a5b6c7d8
Revises: d4a9f1b2c3e5
Create Date: 2026-07-02 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "e3f4a5b6c7d8"
down_revision: Union[str, Sequence[str], None] = "d4a9f1b2c3e5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("projects", sa.Column("target_estimate", sa.BigInteger(), nullable=True))
    op.create_check_constraint(
        "ck_projects_target_estimate_positive",
        "projects",
        "target_estimate IS NULL OR target_estimate > 0",
    )


def downgrade() -> None:
    op.drop_constraint("ck_projects_target_estimate_positive", "projects", type_="check")
    op.drop_column("projects", "target_estimate")
