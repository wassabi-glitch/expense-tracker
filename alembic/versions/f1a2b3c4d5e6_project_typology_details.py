"""project typology details

Revision ID: f1a2b3c4d5e6
Revises: e3f4a5b6c7d8
Create Date: 2026-07-02 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "f1a2b3c4d5e6"
down_revision: Union[str, Sequence[str], None] = "e3f4a5b6c7d8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


project_type_enum = sa.Enum("OVERLAY", "ISOLATED", name="projecttype")


def upgrade() -> None:
    bind = op.get_bind()
    project_type_enum.create(bind, checkfirst=True)
    op.add_column("projects", sa.Column("project_type", project_type_enum, nullable=True))
    if bind.dialect.name == "postgresql":
        op.execute(
            """
            UPDATE projects
            SET project_type = CASE
                WHEN is_isolated THEN 'ISOLATED'::projecttype
                ELSE 'OVERLAY'::projecttype
            END
            """
        )
    else:
        op.execute("UPDATE projects SET project_type = CASE WHEN is_isolated THEN 'ISOLATED' ELSE 'OVERLAY' END")
    op.alter_column("projects", "project_type", existing_type=project_type_enum, nullable=False)

    op.create_table(
        "project_overlay_details",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("project_id", sa.Integer(), nullable=False),
        sa.Column("owner_id", sa.Integer(), nullable=False),
        sa.Column("target_estimate", sa.BigInteger(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint(
            "target_estimate IS NULL OR target_estimate > 0",
            name="ck_project_overlay_details_target_estimate_positive",
        ),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("project_id", name="uq_project_overlay_details_project_id"),
    )
    op.create_index(op.f("ix_project_overlay_details_id"), "project_overlay_details", ["id"], unique=False)
    op.create_index(op.f("ix_project_overlay_details_owner_id"), "project_overlay_details", ["owner_id"], unique=False)
    op.create_index(op.f("ix_project_overlay_details_project_id"), "project_overlay_details", ["project_id"], unique=False)

    op.create_table(
        "project_isolated_details",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("project_id", sa.Integer(), nullable=False),
        sa.Column("owner_id", sa.Integer(), nullable=False),
        sa.Column("funding_limit", sa.BigInteger(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint(
            "funding_limit IS NULL OR funding_limit > 0",
            name="ck_project_isolated_details_funding_limit_positive",
        ),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("project_id", name="uq_project_isolated_details_project_id"),
    )
    op.create_index(op.f("ix_project_isolated_details_id"), "project_isolated_details", ["id"], unique=False)
    op.create_index(op.f("ix_project_isolated_details_owner_id"), "project_isolated_details", ["owner_id"], unique=False)
    op.create_index(op.f("ix_project_isolated_details_project_id"), "project_isolated_details", ["project_id"], unique=False)

    op.execute(
        """
        INSERT INTO project_overlay_details (project_id, owner_id, target_estimate)
        SELECT id, owner_id, target_estimate
        FROM projects
        WHERE project_type = 'OVERLAY'
        """
    )
    op.execute(
        """
        INSERT INTO project_isolated_details (project_id, owner_id, funding_limit)
        SELECT id, owner_id, total_limit
        FROM projects
        WHERE project_type = 'ISOLATED'
        """
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_project_isolated_details_project_id"), table_name="project_isolated_details")
    op.drop_index(op.f("ix_project_isolated_details_owner_id"), table_name="project_isolated_details")
    op.drop_index(op.f("ix_project_isolated_details_id"), table_name="project_isolated_details")
    op.drop_table("project_isolated_details")
    op.drop_index(op.f("ix_project_overlay_details_project_id"), table_name="project_overlay_details")
    op.drop_index(op.f("ix_project_overlay_details_owner_id"), table_name="project_overlay_details")
    op.drop_index(op.f("ix_project_overlay_details_id"), table_name="project_overlay_details")
    op.drop_table("project_overlay_details")
    op.drop_column("projects", "project_type")
    project_type_enum.drop(op.get_bind(), checkfirst=True)
