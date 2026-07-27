"""add security_events table

Revision ID: a1b2c3d4e5f7
Revises: 602f3bc5ab4c
Create Date: 2026-07-25 10:40:00.000000
"""

from typing import Sequence, Union

from alembic import op
# pyrefly: ignore [missing-import]
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "a1b2c3d4e5f7"
down_revision: Union[str, Sequence[str], None] = "602f3bc5ab4c"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Enum values
SECURITY_ACTION_VALUES = (
    "SIGNUP", "EMAIL_VERIFIED", "LOGIN", "GOOGLE_LOGIN",
    "PASSWORD_CHANGED", "PASSWORD_RESET", "LOGOUT_ALL",
)
SECURITY_STATUS_VALUES = ("SUCCESS", "FAILED")


def upgrade() -> None:
    security_action_enum = sa.Enum(
        *SECURITY_ACTION_VALUES, name="securityaction"
    )
    security_status_enum = sa.Enum(
        *SECURITY_STATUS_VALUES, name="securitystatus"
    )

    op.create_table(
        "security_events",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=True),
        sa.Column("action", security_action_enum, nullable=False),
        sa.Column("status", security_status_enum, nullable=False),
        sa.Column("ip_address", sa.String(length=45), nullable=True),
        sa.Column("user_agent", sa.String(length=512), nullable=True),
        sa.Column("metadata", sa.JSON(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_security_events_id"),
        "security_events", ["id"], unique=False,
    )
    op.create_index(
        op.f("ix_security_events_user_id"),
        "security_events", ["user_id"], unique=False,
    )
    op.create_index(
        "ix_security_events_user_id_created_at",
        "security_events", ["user_id", "created_at"], unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_security_events_user_id_created_at",
        table_name="security_events",
    )
    op.drop_index(
        op.f("ix_security_events_user_id"),
        table_name="security_events",
    )
    op.drop_index(
        op.f("ix_security_events_id"),
        table_name="security_events",
    )
    op.drop_table("security_events")

    # Drop the enum types created by upgrade
    sa.Enum(name="securityaction").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="securitystatus").drop(op.get_bind(), checkfirst=True)
