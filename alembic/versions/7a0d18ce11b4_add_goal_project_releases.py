"""add goal project releases

Revision ID: 7a0d18ce11b4
Revises: 5c91b9a4d3e2
Create Date: 2026-05-17 12:10:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "7a0d18ce11b4"
down_revision: Union[str, Sequence[str], None] = "5c91b9a4d3e2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "goal_project_releases",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("owner_id", sa.Integer(), nullable=False),
        sa.Column("goal_id", sa.Integer(), nullable=False),
        sa.Column("project_id", sa.Integer(), nullable=False),
        sa.Column("amount", sa.BigInteger(), nullable=False),
        sa.Column("released_at", sa.Date(), nullable=False),
        sa.Column("note", sa.String(length=500), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("amount > 0", name="ck_goal_project_releases_amount_positive"),
        sa.ForeignKeyConstraint(["goal_id"], ["goals.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_goal_project_releases_id"), "goal_project_releases", ["id"], unique=False)
    op.create_index(op.f("ix_goal_project_releases_owner_id"), "goal_project_releases", ["owner_id"], unique=False)
    op.create_index(op.f("ix_goal_project_releases_goal_id"), "goal_project_releases", ["goal_id"], unique=False)
    op.create_index(op.f("ix_goal_project_releases_project_id"), "goal_project_releases", ["project_id"], unique=False)
    op.create_index("ix_goal_project_releases_goal_created_at", "goal_project_releases", ["goal_id", "created_at"], unique=False)
    op.create_index("ix_goal_project_releases_project_created_at", "goal_project_releases", ["project_id", "created_at"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_goal_project_releases_project_created_at", table_name="goal_project_releases")
    op.drop_index("ix_goal_project_releases_goal_created_at", table_name="goal_project_releases")
    op.drop_index(op.f("ix_goal_project_releases_project_id"), table_name="goal_project_releases")
    op.drop_index(op.f("ix_goal_project_releases_goal_id"), table_name="goal_project_releases")
    op.drop_index(op.f("ix_goal_project_releases_owner_id"), table_name="goal_project_releases")
    op.drop_index(op.f("ix_goal_project_releases_id"), table_name="goal_project_releases")
    op.drop_table("goal_project_releases")
