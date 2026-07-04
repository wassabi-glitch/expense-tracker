"""rename project money mechanics tables

Revision ID: 1a2b3c4d5e6f
Revises: 0a1b2c3d4e6f
Create Date: 2026-07-04 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "1a2b3c4d5e6f"
down_revision: Union[str, Sequence[str], None] = "0a1b2c3d4e6f"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _rename_pg_constraint(table_name: str, old_name: str, new_name: str) -> None:
    op.execute(
        f"""
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1 FROM pg_constraint
                WHERE conname = '{old_name}' AND conrelid = '{table_name}'::regclass
            ) THEN
                ALTER TABLE {table_name} RENAME CONSTRAINT {old_name} TO {new_name};
            END IF;
        END $$;
        """
    )


def _rename_pg_index(old_name: str, new_name: str) -> None:
    op.execute(
        f"""
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1 FROM pg_class
                WHERE relkind = 'i' AND relname = '{old_name}'
            ) THEN
                ALTER INDEX {old_name} RENAME TO {new_name};
            END IF;
        END $$;
        """
    )


def upgrade() -> None:
    op.rename_table("project_wallet_allocations", "isolated_project_wallet_allocations")
    op.rename_table("project_category_limits", "isolated_project_category_allocations")
    op.rename_table("project_category_monthly_limits", "overlay_project_category_reservations")
    op.rename_table("project_subcategory_monthly_limits", "overlay_project_subcategory_reservations")
    op.rename_table("project_subcategories", "legacy_project_subcategories")
    op.create_table(
        "isolated_project_subcategory_allocations",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("project_id", sa.Integer(), nullable=False),
        sa.Column("category_allocation_id", sa.Integer(), nullable=True),
        sa.Column(
            "category",
            postgresql.ENUM(
                "GROCERIES",
                "DINING_OUT",
                "ELECTRONICS",
                "HOUSING",
                "UTILITIES",
                "SUBSCRIPTIONS",
                "TRANSPORT",
                "HEALTH",
                "PERSONAL_CARE",
                "EDUCATION",
                "CLOTHING",
                "FAMILY_EVENTS",
                "ENTERTAINMENT",
                "PAYMENT_PLANS_DEBT",
                "BUSINESS_WORK",
                "BANK_FEES_INTEREST",
                "DEBT_CHARGES",
                "TRAVEL",
                "CHARITY",
                "ANIMALS_PETS",
                name="expensecategory",
                create_type=False,
            ),
            nullable=False,
        ),
        sa.Column("user_subcategory_id", sa.Integer(), nullable=False),
        sa.Column("allocated_amount", sa.BigInteger(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("allocated_amount > 0", name="ck_isolated_project_subcategory_allocations_amount_positive"),
        sa.CheckConstraint("allocated_amount <= 999999999999", name="ck_isolated_project_subcategory_allocations_amount_max"),
        sa.ForeignKeyConstraint(["category_allocation_id"], ["isolated_project_category_allocations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_subcategory_id"], ["user_subcategories.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("project_id", "user_subcategory_id", name="uq_isolated_project_subcategory_allocations_project_taxonomy"),
    )
    op.create_index(
        op.f("ix_isolated_project_subcategory_allocations_id"),
        "isolated_project_subcategory_allocations",
        ["id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_isolated_project_subcategory_allocations_project_id"),
        "isolated_project_subcategory_allocations",
        ["project_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_isolated_project_subcategory_allocations_category_allocation_id"),
        "isolated_project_subcategory_allocations",
        ["category_allocation_id"],
        unique=False,
    )
    op.create_index(
        "ix_isolated_project_subcategory_allocations_project_category",
        "isolated_project_subcategory_allocations",
        ["project_id", "category"],
        unique=False,
    )
    op.create_index(
        "ix_isolated_project_subcategory_allocations_taxonomy",
        "isolated_project_subcategory_allocations",
        ["user_subcategory_id"],
        unique=False,
    )

    if op.get_bind().dialect.name != "postgresql":
        return

    _rename_pg_constraint(
        "isolated_project_wallet_allocations",
        "uq_project_wallet_allocations_project_wallet",
        "uq_isolated_project_wallet_allocations_project_wallet",
    )
    _rename_pg_constraint(
        "isolated_project_wallet_allocations",
        "ck_project_wallet_allocations_amount_positive",
        "ck_isolated_project_wallet_allocations_amount_positive",
    )
    _rename_pg_constraint(
        "isolated_project_wallet_allocations",
        "ck_project_wallet_allocations_amount_max",
        "ck_isolated_project_wallet_allocations_amount_max",
    )
    _rename_pg_index("ix_project_wallet_allocations_id", "ix_isolated_project_wallet_allocations_id")
    _rename_pg_index("ix_project_wallet_allocations_owner_id", "ix_isolated_project_wallet_allocations_owner_id")
    _rename_pg_index("ix_project_wallet_allocations_project_id", "ix_isolated_project_wallet_allocations_project_id")
    _rename_pg_index("ix_project_wallet_allocations_wallet_id", "ix_isolated_project_wallet_allocations_wallet_id")
    _rename_pg_index("ix_project_wallet_allocations_owner_wallet", "ix_isolated_project_wallet_allocations_owner_wallet")

    _rename_pg_constraint(
        "isolated_project_category_allocations",
        "uq_project_category_limits",
        "uq_isolated_project_category_allocations_project_category",
    )
    _rename_pg_index("ix_project_category_limits_id", "ix_isolated_project_category_allocations_id")
    _rename_pg_index("ix_project_category_limits_project_id", "ix_isolated_project_category_allocations_project_id")

    _rename_pg_constraint(
        "overlay_project_category_reservations",
        "uq_project_category_monthly_limits_project_category_month",
        "uq_overlay_project_category_reservations_project_category_month",
    )
    _rename_pg_constraint(
        "overlay_project_category_reservations",
        "ck_project_category_monthly_limits_month",
        "ck_overlay_project_category_reservations_month",
    )
    _rename_pg_constraint(
        "overlay_project_category_reservations",
        "ck_project_category_monthly_limits_year",
        "ck_overlay_project_category_reservations_year",
    )
    _rename_pg_constraint(
        "overlay_project_category_reservations",
        "ck_project_category_monthly_limits_amount_positive",
        "ck_overlay_project_category_reservations_amount_positive",
    )
    _rename_pg_constraint(
        "overlay_project_category_reservations",
        "ck_project_category_monthly_limits_amount_max",
        "ck_overlay_project_category_reservations_amount_max",
    )
    _rename_pg_index("ix_project_category_monthly_limits_id", "ix_overlay_project_category_reservations_id")
    _rename_pg_index("ix_project_category_monthly_limits_project_id", "ix_overlay_project_category_reservations_project_id")
    _rename_pg_index("ix_project_category_monthly_limits_month", "ix_overlay_project_category_reservations_month")

    _rename_pg_constraint(
        "overlay_project_subcategory_reservations",
        "uq_project_subcategory_monthly_limits_project_subcategory_month",
        "uq_overlay_project_subcategory_reservations_project_subcategory_month",
    )
    _rename_pg_constraint(
        "overlay_project_subcategory_reservations",
        "ck_project_subcategory_monthly_limits_month",
        "ck_overlay_project_subcategory_reservations_month",
    )
    _rename_pg_constraint(
        "overlay_project_subcategory_reservations",
        "ck_project_subcategory_monthly_limits_year",
        "ck_overlay_project_subcategory_reservations_year",
    )
    _rename_pg_constraint(
        "overlay_project_subcategory_reservations",
        "ck_project_subcategory_monthly_limits_amount_positive",
        "ck_overlay_project_subcategory_reservations_amount_positive",
    )
    _rename_pg_constraint(
        "overlay_project_subcategory_reservations",
        "ck_project_subcategory_monthly_limits_amount_max",
        "ck_overlay_project_subcategory_reservations_amount_max",
    )
    _rename_pg_index("ix_project_subcategory_monthly_limits_id", "ix_overlay_project_subcategory_reservations_id")
    _rename_pg_index("ix_project_subcategory_monthly_limits_project_id", "ix_overlay_project_subcategory_reservations_project_id")
    _rename_pg_index("ix_project_subcategory_monthly_limits_month", "ix_overlay_project_subcategory_reservations_month")
    _rename_pg_index("ix_project_subcategory_monthly_limits_subcategory", "ix_overlay_project_subcategory_reservations_subcategory")

    _rename_pg_constraint(
        "legacy_project_subcategories",
        "uq_project_subcategories_project_category_name",
        "uq_legacy_project_subcategories_project_category_name",
    )
    _rename_pg_index("ix_project_subcategories_id", "ix_legacy_project_subcategories_id")
    _rename_pg_index("ix_project_subcategories_project_id", "ix_legacy_project_subcategories_project_id")
    _rename_pg_index("ix_project_subcategories_project_category", "ix_legacy_project_subcategories_project_category")


def downgrade() -> None:
    if op.get_bind().dialect.name == "postgresql":
        _rename_pg_constraint(
            "legacy_project_subcategories",
            "uq_legacy_project_subcategories_project_category_name",
            "uq_project_subcategories_project_category_name",
        )
        _rename_pg_index("ix_legacy_project_subcategories_id", "ix_project_subcategories_id")
        _rename_pg_index("ix_legacy_project_subcategories_project_id", "ix_project_subcategories_project_id")
        _rename_pg_index("ix_legacy_project_subcategories_project_category", "ix_project_subcategories_project_category")

        _rename_pg_constraint(
            "overlay_project_subcategory_reservations",
            "uq_overlay_project_subcategory_reservations_project_subcategory_month",
            "uq_project_subcategory_monthly_limits_project_subcategory_month",
        )
        _rename_pg_constraint(
            "overlay_project_subcategory_reservations",
            "ck_overlay_project_subcategory_reservations_month",
            "ck_project_subcategory_monthly_limits_month",
        )
        _rename_pg_constraint(
            "overlay_project_subcategory_reservations",
            "ck_overlay_project_subcategory_reservations_year",
            "ck_project_subcategory_monthly_limits_year",
        )
        _rename_pg_constraint(
            "overlay_project_subcategory_reservations",
            "ck_overlay_project_subcategory_reservations_amount_positive",
            "ck_project_subcategory_monthly_limits_amount_positive",
        )
        _rename_pg_constraint(
            "overlay_project_subcategory_reservations",
            "ck_overlay_project_subcategory_reservations_amount_max",
            "ck_project_subcategory_monthly_limits_amount_max",
        )
        _rename_pg_index("ix_overlay_project_subcategory_reservations_id", "ix_project_subcategory_monthly_limits_id")
        _rename_pg_index("ix_overlay_project_subcategory_reservations_project_id", "ix_project_subcategory_monthly_limits_project_id")
        _rename_pg_index("ix_overlay_project_subcategory_reservations_month", "ix_project_subcategory_monthly_limits_month")
        _rename_pg_index("ix_overlay_project_subcategory_reservations_subcategory", "ix_project_subcategory_monthly_limits_subcategory")

        _rename_pg_constraint(
            "overlay_project_category_reservations",
            "uq_overlay_project_category_reservations_project_category_month",
            "uq_project_category_monthly_limits_project_category_month",
        )
        _rename_pg_constraint(
            "overlay_project_category_reservations",
            "ck_overlay_project_category_reservations_month",
            "ck_project_category_monthly_limits_month",
        )
        _rename_pg_constraint(
            "overlay_project_category_reservations",
            "ck_overlay_project_category_reservations_year",
            "ck_project_category_monthly_limits_year",
        )
        _rename_pg_constraint(
            "overlay_project_category_reservations",
            "ck_overlay_project_category_reservations_amount_positive",
            "ck_project_category_monthly_limits_amount_positive",
        )
        _rename_pg_constraint(
            "overlay_project_category_reservations",
            "ck_overlay_project_category_reservations_amount_max",
            "ck_project_category_monthly_limits_amount_max",
        )
        _rename_pg_index("ix_overlay_project_category_reservations_id", "ix_project_category_monthly_limits_id")
        _rename_pg_index("ix_overlay_project_category_reservations_project_id", "ix_project_category_monthly_limits_project_id")
        _rename_pg_index("ix_overlay_project_category_reservations_month", "ix_project_category_monthly_limits_month")

        _rename_pg_constraint(
            "isolated_project_category_allocations",
            "uq_isolated_project_category_allocations_project_category",
            "uq_project_category_limits",
        )
        _rename_pg_index("ix_isolated_project_category_allocations_id", "ix_project_category_limits_id")
        _rename_pg_index("ix_isolated_project_category_allocations_project_id", "ix_project_category_limits_project_id")

        _rename_pg_constraint(
            "isolated_project_wallet_allocations",
            "uq_isolated_project_wallet_allocations_project_wallet",
            "uq_project_wallet_allocations_project_wallet",
        )
        _rename_pg_constraint(
            "isolated_project_wallet_allocations",
            "ck_isolated_project_wallet_allocations_amount_positive",
            "ck_project_wallet_allocations_amount_positive",
        )
        _rename_pg_constraint(
            "isolated_project_wallet_allocations",
            "ck_isolated_project_wallet_allocations_amount_max",
            "ck_project_wallet_allocations_amount_max",
        )
        _rename_pg_index("ix_isolated_project_wallet_allocations_id", "ix_project_wallet_allocations_id")
        _rename_pg_index("ix_isolated_project_wallet_allocations_owner_id", "ix_project_wallet_allocations_owner_id")
        _rename_pg_index("ix_isolated_project_wallet_allocations_project_id", "ix_project_wallet_allocations_project_id")
        _rename_pg_index("ix_isolated_project_wallet_allocations_wallet_id", "ix_project_wallet_allocations_wallet_id")
        _rename_pg_index("ix_isolated_project_wallet_allocations_owner_wallet", "ix_project_wallet_allocations_owner_wallet")

    op.drop_index("ix_isolated_project_subcategory_allocations_taxonomy", table_name="isolated_project_subcategory_allocations")
    op.drop_index("ix_isolated_project_subcategory_allocations_project_category", table_name="isolated_project_subcategory_allocations")
    op.drop_index(op.f("ix_isolated_project_subcategory_allocations_category_allocation_id"), table_name="isolated_project_subcategory_allocations")
    op.drop_index(op.f("ix_isolated_project_subcategory_allocations_project_id"), table_name="isolated_project_subcategory_allocations")
    op.drop_index(op.f("ix_isolated_project_subcategory_allocations_id"), table_name="isolated_project_subcategory_allocations")
    op.drop_table("isolated_project_subcategory_allocations")
    op.rename_table("legacy_project_subcategories", "project_subcategories")
    op.rename_table("overlay_project_subcategory_reservations", "project_subcategory_monthly_limits")
    op.rename_table("overlay_project_category_reservations", "project_category_monthly_limits")
    op.rename_table("isolated_project_category_allocations", "project_category_limits")
    op.rename_table("isolated_project_wallet_allocations", "project_wallet_allocations")
