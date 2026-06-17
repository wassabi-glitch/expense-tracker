"""wallet backed goal allocations

Revision ID: aa4d8c9f0b21
Revises: 4a6c7285ade1
Create Date: 2026-05-23 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "aa4d8c9f0b21"
down_revision: Union[str, Sequence[str], None] = "4a6c7285ade1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()

    if bind.dialect.name == "postgresql":
        with op.get_context().autocommit_block():
            op.execute("ALTER TYPE wallettype ADD VALUE IF NOT EXISTS 'SAVINGS'")
            op.execute("ALTER TYPE goalcontributiontype ADD VALUE IF NOT EXISTS 'CONSUME'")
        goal_intent = postgresql.ENUM(
            "GENERAL_SAVINGS",
            "EMERGENCY_RESERVE",
            "PURCHASE_ASSET",
            "PAY_DEBT",
            "FUND_INSTALLMENT",
            "FUND_PROJECT",
            "FUTURE_EXPENSE",
            name="goalintent",
        )
        goal_intent.create(bind, checkfirst=True)
        goal_intent_type = goal_intent
    else:
        goal_intent_type = sa.Enum(
            "GENERAL_SAVINGS",
            "EMERGENCY_RESERVE",
            "PURCHASE_ASSET",
            "PAY_DEBT",
            "FUND_INSTALLMENT",
            "FUND_PROJECT",
            "FUTURE_EXPENSE",
            name="goalintent",
        )

    op.execute("DELETE FROM goal_project_releases")
    op.execute("DELETE FROM goal_contributions")
    op.execute("DELETE FROM savings_transactions")
    op.execute("UPDATE budgets SET sweep_target_goal_id = NULL")

    op.add_column("wallets", sa.Column("can_fund_goals", sa.Boolean(), server_default=sa.false(), nullable=False))
    op.drop_constraint("ck_wallets_initial_balance_integrity", "wallets", type_="check")
    op.create_check_constraint(
        "ck_wallets_initial_balance_integrity",
        "wallets",
        "(wallet_type = 'CREDIT') OR "
        "((wallet_type = 'CASH' OR wallet_type = 'SAVINGS') AND initial_balance >= 0) OR "
        "((wallet_type = 'DEBIT' OR wallet_type = 'PRELOADED') AND (has_overdraft = TRUE OR initial_balance >= 0))",
    )
    op.create_check_constraint(
        "ck_wallets_goal_funding_owned_money_only",
        "wallets",
        "(wallet_type != 'CREDIT' AND accounting_type = 'ASSET') OR can_fund_goals = FALSE",
    )

    op.add_column("goals", sa.Column("currency", sa.String(length=3), server_default="UZS", nullable=False))
    op.add_column("goals", sa.Column("intent", goal_intent_type, server_default="GENERAL_SAVINGS", nullable=False))
    op.add_column("goals", sa.Column("linked_asset_id", sa.Integer(), nullable=True))
    op.add_column("goals", sa.Column("linked_debt_id", sa.Integer(), nullable=True))
    op.add_column("goals", sa.Column("linked_installment_plan_id", sa.Integer(), nullable=True))
    op.add_column("goals", sa.Column("linked_expense_event_id", sa.Integer(), nullable=True))
    op.create_index(op.f("ix_goals_linked_asset_id"), "goals", ["linked_asset_id"], unique=False)
    op.create_index(op.f("ix_goals_linked_debt_id"), "goals", ["linked_debt_id"], unique=False)
    op.create_index(op.f("ix_goals_linked_installment_plan_id"), "goals", ["linked_installment_plan_id"], unique=False)
    op.create_index(op.f("ix_goals_linked_expense_event_id"), "goals", ["linked_expense_event_id"], unique=False)
    op.create_foreign_key("fk_goals_linked_asset_id", "goals", "assets", ["linked_asset_id"], ["id"], ondelete="SET NULL")
    op.create_foreign_key("fk_goals_linked_debt_id", "goals", "debts", ["linked_debt_id"], ["id"], ondelete="SET NULL")
    op.create_foreign_key(
        "fk_goals_linked_installment_plan_id",
        "goals",
        "installment_plans",
        ["linked_installment_plan_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_foreign_key(
        "fk_goals_linked_expense_event_id",
        "goals",
        "financial_events",
        ["linked_expense_event_id"],
        ["id"],
        ondelete="SET NULL",
    )

    op.add_column("goal_contributions", sa.Column("wallet_id", sa.Integer(), nullable=False))
    op.add_column("goal_contributions", sa.Column("linked_event_id", sa.Integer(), nullable=True))
    op.create_index("ix_goal_contributions_wallet_created_at", "goal_contributions", ["wallet_id", "created_at"], unique=False)
    op.create_index(op.f("ix_goal_contributions_wallet_id"), "goal_contributions", ["wallet_id"], unique=False)
    op.create_index(op.f("ix_goal_contributions_linked_event_id"), "goal_contributions", ["linked_event_id"], unique=False)
    op.create_foreign_key("fk_goal_contributions_wallet_id", "goal_contributions", "wallets", ["wallet_id"], ["id"], ondelete="RESTRICT")
    op.create_foreign_key(
        "fk_goal_contributions_linked_event_id",
        "goal_contributions",
        "financial_events",
        ["linked_event_id"],
        ["id"],
        ondelete="SET NULL",
    )

    op.add_column("goal_project_releases", sa.Column("wallet_id", sa.Integer(), nullable=True))
    op.create_index(op.f("ix_goal_project_releases_wallet_id"), "goal_project_releases", ["wallet_id"], unique=False)
    op.create_foreign_key("fk_goal_project_releases_wallet_id", "goal_project_releases", "wallets", ["wallet_id"], ["id"], ondelete="RESTRICT")


def downgrade() -> None:
    op.drop_constraint("fk_goal_project_releases_wallet_id", "goal_project_releases", type_="foreignkey")
    op.drop_index(op.f("ix_goal_project_releases_wallet_id"), table_name="goal_project_releases")
    op.drop_column("goal_project_releases", "wallet_id")

    op.drop_constraint("fk_goal_contributions_linked_event_id", "goal_contributions", type_="foreignkey")
    op.drop_constraint("fk_goal_contributions_wallet_id", "goal_contributions", type_="foreignkey")
    op.drop_index(op.f("ix_goal_contributions_linked_event_id"), table_name="goal_contributions")
    op.drop_index(op.f("ix_goal_contributions_wallet_id"), table_name="goal_contributions")
    op.drop_index("ix_goal_contributions_wallet_created_at", table_name="goal_contributions")
    op.drop_column("goal_contributions", "linked_event_id")
    op.drop_column("goal_contributions", "wallet_id")

    op.drop_constraint("fk_goals_linked_expense_event_id", "goals", type_="foreignkey")
    op.drop_constraint("fk_goals_linked_installment_plan_id", "goals", type_="foreignkey")
    op.drop_constraint("fk_goals_linked_debt_id", "goals", type_="foreignkey")
    op.drop_constraint("fk_goals_linked_asset_id", "goals", type_="foreignkey")
    op.drop_index(op.f("ix_goals_linked_expense_event_id"), table_name="goals")
    op.drop_index(op.f("ix_goals_linked_installment_plan_id"), table_name="goals")
    op.drop_index(op.f("ix_goals_linked_debt_id"), table_name="goals")
    op.drop_index(op.f("ix_goals_linked_asset_id"), table_name="goals")
    op.drop_column("goals", "linked_expense_event_id")
    op.drop_column("goals", "linked_installment_plan_id")
    op.drop_column("goals", "linked_debt_id")
    op.drop_column("goals", "linked_asset_id")
    op.drop_column("goals", "intent")
    op.drop_column("goals", "currency")

    op.drop_constraint("ck_wallets_goal_funding_owned_money_only", "wallets", type_="check")
    op.drop_constraint("ck_wallets_initial_balance_integrity", "wallets", type_="check")
    op.create_check_constraint(
        "ck_wallets_initial_balance_integrity",
        "wallets",
        "(wallet_type = 'CREDIT') OR "
        "(wallet_type = 'CASH' AND initial_balance >= 0) OR "
        "((wallet_type = 'DEBIT' OR wallet_type = 'PRELOADED') AND (has_overdraft = TRUE OR initial_balance >= 0))",
    )
    op.drop_column("wallets", "can_fund_goals")

    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        postgresql.ENUM(name="goalintent").drop(bind, checkfirst=True)
