"""drop project legacy typology fields

Revision ID: f2b3c4d5e6f7
Revises: f1a2b3c4d5e6
Create Date: 2026-07-02 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "f2b3c4d5e6f7"
down_revision: Union[str, Sequence[str], None] = "f1a2b3c4d5e6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.drop_constraint("ck_projects_target_estimate_positive", "projects", type_="check")
    op.drop_column("projects", "target_estimate")
    op.drop_column("projects", "total_limit")
    op.drop_column("projects", "is_isolated")


def downgrade() -> None:
    op.add_column("projects", sa.Column("is_isolated", sa.Boolean(), nullable=True))
    op.add_column("projects", sa.Column("total_limit", sa.BigInteger(), nullable=True))
    op.add_column("projects", sa.Column("target_estimate", sa.BigInteger(), nullable=True))
    op.create_check_constraint(
        "ck_projects_target_estimate_positive",
        "projects",
        "target_estimate IS NULL OR target_estimate > 0",
    )
    op.execute(
        """
        UPDATE projects
        SET is_isolated = CASE WHEN project_type = 'ISOLATED' THEN true ELSE false END
        """
    )
    op.execute(
        """
        UPDATE projects
        SET total_limit = detail.funding_limit
        FROM project_isolated_details AS detail
        WHERE detail.project_id = projects.id
        """
    )
    op.execute(
        """
        UPDATE projects
        SET target_estimate = detail.target_estimate
        FROM project_overlay_details AS detail
        WHERE detail.project_id = projects.id
        """
    )
    op.alter_column("projects", "is_isolated", existing_type=sa.Boolean(), nullable=False)
