"""add unique origin goal to projects

Revision ID: 8f2c44dbe93a
Revises: 7a0d18ce11b4
Create Date: 2026-05-17 12:35:00.000000

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "8f2c44dbe93a"
down_revision: Union[str, Sequence[str], None] = "7a0d18ce11b4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_unique_constraint("uq_projects_origin_goal_id", "projects", ["origin_goal_id"])


def downgrade() -> None:
    op.drop_constraint("uq_projects_origin_goal_id", "projects", type_="unique")
