"""remove debt action restriction persistence

Revision ID: b6c7d8e9f0a1
Revises: 29e810b4fc08
Create Date: 2026-06-27 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "b6c7d8e9f0a1"
down_revision: Union[str, Sequence[str], None] = "29e810b4fc08"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


DEBT_ACTION_KINDS = (
    "RECORD_PAYMENT",
    "ADD_CHARGE",
    "FORGIVE_PARTIAL",
    "FORGIVE_FULL",
    "ADJUST_BALANCE",
    "REVERSE_ENTRY",
    "SETTLE",
    "ARCHIVE",
    "RESTORE",
    "LINK_ASSET",
    "SET_COLLATERAL",
    "RESTRUCTURE_TERMS",
)

DEBT_ACTION_RESTRICTION_LEVELS = (
    "BLOCKED",
    "REQUIRES_CONFIRMATION",
    "UNDO_UNAVAILABLE",
)

DEBT_ACTION_RESTRICTION_SOURCES = (
    "SYSTEM",
    "USER",
    "POLICY",
)


def _table_exists(table_name: str) -> bool:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    return table_name in inspector.get_table_names()


def _drop_postgresql_type_if_exists(type_name: str) -> None:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.execute(sa.text(f"DROP TYPE IF EXISTS {type_name}"))


def _action_kind_enum():
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        return postgresql.ENUM(*DEBT_ACTION_KINDS, name="debtactionkind", create_type=False)
    return sa.Enum(*DEBT_ACTION_KINDS, name="debtactionkind")


def _restriction_level_enum():
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        return postgresql.ENUM(
            *DEBT_ACTION_RESTRICTION_LEVELS,
            name="debtactionrestrictionlevel",
            create_type=False,
        )
    return sa.Enum(*DEBT_ACTION_RESTRICTION_LEVELS, name="debtactionrestrictionlevel")


def _restriction_source_enum():
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        return postgresql.ENUM(
            *DEBT_ACTION_RESTRICTION_SOURCES,
            name="debtactionrestrictionsource",
            create_type=False,
        )
    return sa.Enum(*DEBT_ACTION_RESTRICTION_SOURCES, name="debtactionrestrictionsource")


def _create_postgresql_enum_types_if_needed() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        postgresql.ENUM(*DEBT_ACTION_KINDS, name="debtactionkind").create(bind, checkfirst=True)
        postgresql.ENUM(
            *DEBT_ACTION_RESTRICTION_LEVELS,
            name="debtactionrestrictionlevel",
        ).create(bind, checkfirst=True)
        postgresql.ENUM(
            *DEBT_ACTION_RESTRICTION_SOURCES,
            name="debtactionrestrictionsource",
        ).create(bind, checkfirst=True)


def upgrade() -> None:
    if _table_exists("debt_action_restrictions"):
        op.drop_index("ix_debt_action_restrictions_owner_action", table_name="debt_action_restrictions")
        op.drop_index("ix_debt_action_restrictions_debt_active", table_name="debt_action_restrictions")
        op.drop_index(op.f("ix_debt_action_restrictions_debt_id"), table_name="debt_action_restrictions")
        op.drop_index(op.f("ix_debt_action_restrictions_owner_id"), table_name="debt_action_restrictions")
        op.drop_index(op.f("ix_debt_action_restrictions_id"), table_name="debt_action_restrictions")
        op.drop_table("debt_action_restrictions")

    _drop_postgresql_type_if_exists("debtactionrestrictionsource")
    _drop_postgresql_type_if_exists("debtactionrestrictionlevel")
    _drop_postgresql_type_if_exists("debtactionkind")


def downgrade() -> None:
    action_kind = _action_kind_enum()
    restriction_level = _restriction_level_enum()
    restriction_source = _restriction_source_enum()

    _create_postgresql_enum_types_if_needed()

    op.create_table(
        "debt_action_restrictions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("owner_id", sa.Integer(), nullable=False),
        sa.Column("debt_id", sa.Integer(), nullable=False),
        sa.Column("action_kind", action_kind, nullable=False),
        sa.Column("level", restriction_level, nullable=False),
        sa.Column("reason_code", sa.String(length=100), nullable=False),
        sa.Column("source", restriction_source, server_default="SYSTEM", nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("details", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["debt_id"], ["debts.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_debt_action_restrictions_id"), "debt_action_restrictions", ["id"], unique=False)
    op.create_index(op.f("ix_debt_action_restrictions_owner_id"), "debt_action_restrictions", ["owner_id"], unique=False)
    op.create_index(op.f("ix_debt_action_restrictions_debt_id"), "debt_action_restrictions", ["debt_id"], unique=False)
    op.create_index("ix_debt_action_restrictions_debt_active", "debt_action_restrictions", ["debt_id", "is_active"], unique=False)
    op.create_index("ix_debt_action_restrictions_owner_action", "debt_action_restrictions", ["owner_id", "action_kind"], unique=False)
