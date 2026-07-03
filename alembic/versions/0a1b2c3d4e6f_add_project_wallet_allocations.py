"""add project wallet allocations

Revision ID: 0a1b2c3d4e6f
Revises: f2b3c4d5e6f7
Create Date: 2026-07-04 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0a1b2c3d4e6f"
down_revision: Union[str, Sequence[str], None] = "f2b3c4d5e6f7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "project_wallet_allocations",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("project_id", sa.Integer(), nullable=False),
        sa.Column("owner_id", sa.Integer(), nullable=False),
        sa.Column("wallet_id", sa.Integer(), nullable=False),
        sa.Column("amount", sa.BigInteger(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("amount > 0", name="ck_project_wallet_allocations_amount_positive"),
        sa.CheckConstraint("amount <= 999999999999", name="ck_project_wallet_allocations_amount_max"),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["wallet_id"], ["wallets.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("project_id", "wallet_id", name="uq_project_wallet_allocations_project_wallet"),
    )
    op.create_index(op.f("ix_project_wallet_allocations_id"), "project_wallet_allocations", ["id"], unique=False)
    op.create_index(op.f("ix_project_wallet_allocations_owner_id"), "project_wallet_allocations", ["owner_id"], unique=False)
    op.create_index(
        "ix_project_wallet_allocations_owner_wallet",
        "project_wallet_allocations",
        ["owner_id", "wallet_id"],
        unique=False,
    )
    op.create_index(op.f("ix_project_wallet_allocations_project_id"), "project_wallet_allocations", ["project_id"], unique=False)
    op.create_index(op.f("ix_project_wallet_allocations_wallet_id"), "project_wallet_allocations", ["wallet_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_project_wallet_allocations_wallet_id"), table_name="project_wallet_allocations")
    op.drop_index(op.f("ix_project_wallet_allocations_project_id"), table_name="project_wallet_allocations")
    op.drop_index("ix_project_wallet_allocations_owner_wallet", table_name="project_wallet_allocations")
    op.drop_index(op.f("ix_project_wallet_allocations_owner_id"), table_name="project_wallet_allocations")
    op.drop_index(op.f("ix_project_wallet_allocations_id"), table_name="project_wallet_allocations")
    op.drop_table("project_wallet_allocations")
