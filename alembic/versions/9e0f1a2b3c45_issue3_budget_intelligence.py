"""issue 3 budget intelligence

Revision ID: 9e0f1a2b3c45
Revises: 8d9e0f1a2b34
Create Date: 2026-06-21 18:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "9e0f1a2b3c45"
down_revision: Union[str, Sequence[str], None] = "8d9e0f1a2b34"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "wallet_ledger",
        sa.Column("owned_spend_amount", sa.BigInteger(), nullable=True),
    )
    op.add_column(
        "wallet_ledger",
        sa.Column("borrowed_spend_amount", sa.BigInteger(), nullable=True),
    )
    op.create_check_constraint(
        "ck_wallet_ledger_owned_spend_non_negative",
        "wallet_ledger",
        "owned_spend_amount IS NULL OR owned_spend_amount >= 0",
    )
    op.create_check_constraint(
        "ck_wallet_ledger_borrowed_spend_non_negative",
        "wallet_ledger",
        "borrowed_spend_amount IS NULL OR borrowed_spend_amount >= 0",
    )

    op.create_table(
        "borrowing_survival_plans",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("owner_id", sa.Integer(), nullable=False),
        sa.Column("budget_year", sa.Integer(), nullable=False),
        sa.Column("budget_month", sa.Integer(), nullable=False),
        sa.Column("enabled", sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.Column("monthly_cap", sa.BigInteger(), server_default="0", nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "monthly_cap >= 0 AND monthly_cap <= 999999999999",
            name="ck_borrowing_survival_cap",
        ),
        sa.CheckConstraint(
            "budget_month >= 1 AND budget_month <= 12",
            name="ck_borrowing_survival_month",
        ),
        sa.CheckConstraint("budget_year >= 2020", name="ck_borrowing_survival_year"),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "owner_id",
            "budget_year",
            "budget_month",
            name="uq_borrowing_survival_owner_month",
        ),
    )
    op.create_index(
        op.f("ix_borrowing_survival_plans_id"),
        "borrowing_survival_plans",
        ["id"],
    )
    op.create_index(
        op.f("ix_borrowing_survival_plans_owner_id"),
        "borrowing_survival_plans",
        ["owner_id"],
    )
    op.create_index(
        "ix_borrowing_survival_owner_month",
        "borrowing_survival_plans",
        ["owner_id", "budget_year", "budget_month"],
    )

    op.drop_constraint(
        "ck_wallets_goal_funding_owned_money_only",
        "wallets",
        type_="check",
    )
    op.create_check_constraint(
        "ck_wallets_goal_funding_owned_money_only",
        "wallets",
        "accounting_type = 'ASSET' OR wallet_type = 'CREDIT' OR can_fund_goals = FALSE",
    )


def downgrade() -> None:
    # Older application versions cannot safely expose credit wallets for goals.
    op.execute("UPDATE wallets SET can_fund_goals = FALSE WHERE wallet_type = 'CREDIT'")
    op.drop_constraint(
        "ck_wallets_goal_funding_owned_money_only",
        "wallets",
        type_="check",
    )
    op.create_check_constraint(
        "ck_wallets_goal_funding_owned_money_only",
        "wallets",
        "(wallet_type != 'CREDIT' AND accounting_type = 'ASSET') OR can_fund_goals = FALSE",
    )

    op.drop_index(
        "ix_borrowing_survival_owner_month",
        table_name="borrowing_survival_plans",
    )
    op.drop_index(
        op.f("ix_borrowing_survival_plans_owner_id"),
        table_name="borrowing_survival_plans",
    )
    op.drop_index(
        op.f("ix_borrowing_survival_plans_id"),
        table_name="borrowing_survival_plans",
    )
    op.drop_table("borrowing_survival_plans")

    op.drop_constraint(
        "ck_wallet_ledger_borrowed_spend_non_negative",
        "wallet_ledger",
        type_="check",
    )
    op.drop_constraint(
        "ck_wallet_ledger_owned_spend_non_negative",
        "wallet_ledger",
        type_="check",
    )
    op.drop_column("wallet_ledger", "borrowed_spend_amount")
    op.drop_column("wallet_ledger", "owned_spend_amount")
