"""add user_profiles

Revision ID: c1bce7a2d116
Revises: 4e856246e7b7
Create Date: 2026-03-10 01:12:52.400430

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'c1bce7a2d116'
down_revision: Union[str, Sequence[str], None] = '4e856246e7b7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.execute(
        "DO $$ BEGIN "
        "IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'lifestatus') THEN "
        "CREATE TYPE lifestatus AS ENUM ("
        "'STUDENT', 'EMPLOYED', 'SELF_EMPLOYED', 'BUSINESS_OWNER', 'UNEMPLOYED'"
        "); "
        "END IF; "
        "END $$;"
    )

    life_status_enum = postgresql.ENUM(
        "STUDENT",
        "EMPLOYED",
        "SELF_EMPLOYED",
        "BUSINESS_OWNER",
        "UNEMPLOYED",
        name="lifestatus",
        create_type=False,
    )

    op.create_table(
        "user_profiles",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("life_status", life_status_enum, nullable=False),
        sa.Column("monthly_income_amount", sa.BigInteger(), nullable=False),
        sa.Column("onboarding_completed_at", sa.DateTime(
            timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True),
                  server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True),
                  server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint(
            "monthly_income_amount >= 0",
            name="ck_user_profiles_monthly_income_amount_non_negative",
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", name="uq_user_profiles_user_id"),
    )

    op.create_index(op.f("ix_user_profiles_id"),
                    "user_profiles", ["id"], unique=False)
    op.create_index(op.f("ix_user_profiles_user_id"),
                    "user_profiles", ["user_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_user_profiles_user_id"), table_name="user_profiles")
    op.drop_index(op.f("ix_user_profiles_id"), table_name="user_profiles")
    op.drop_table("user_profiles")
    op.execute("DROP TYPE IF EXISTS lifestatus")
