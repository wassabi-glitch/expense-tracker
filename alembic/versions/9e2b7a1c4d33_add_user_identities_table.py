"""add user_identities table

Revision ID: 9e2b7a1c4d33
Revises: 4f1a9f8d2c10
Create Date: 2026-02-20 00:00:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "9e2b7a1c4d33"
down_revision: Union[str, Sequence[str], None] = "4f1a9f8d2c10"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "user_identities",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("provider", sa.String(length=50), nullable=False),
        sa.Column("provider_user_id", sa.String(length=255), nullable=False),
        sa.Column("provider_email", sa.String(length=255), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "provider",
            "provider_user_id",
            name="uq_provider_provider_user_id",
        ),
    )
    op.create_index(op.f("ix_user_identities_id"), "user_identities", ["id"], unique=False)
    op.create_index(op.f("ix_user_identities_user_id"), "user_identities", ["user_id"], unique=False)

    # Backfill local identities for existing users.
    op.execute(
        """
        INSERT INTO user_identities (user_id, provider, provider_user_id, provider_email)
        SELECT u.id, 'local', u.id::text, u.email
        FROM users u
        WHERE NOT EXISTS (
            SELECT 1
            FROM user_identities ui
            WHERE ui.user_id = u.id AND ui.provider = 'local'
        )
        """
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_user_identities_user_id"), table_name="user_identities")
    op.drop_index(op.f("ix_user_identities_id"), table_name="user_identities")
    op.drop_table("user_identities")
