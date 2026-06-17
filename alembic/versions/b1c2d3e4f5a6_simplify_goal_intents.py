"""simplify goal intents

Revision ID: b1c2d3e4f5a6
Revises: aa4d8c9f0b21
Create Date: 2026-05-23 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "b1c2d3e4f5a6"
down_revision: Union[str, Sequence[str], None] = "aa4d8c9f0b21"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


NEW_INTENTS = ("RESERVE", "PLANNED_PURCHASE", "PAY_OBLIGATION", "FUND_PROJECT")
OLD_INTENTS = (
    "GENERAL_SAVINGS",
    "EMERGENCY_RESERVE",
    "PURCHASE_ASSET",
    "PAY_DEBT",
    "FUND_INSTALLMENT",
    "FUND_PROJECT",
    "FUTURE_EXPENSE",
)


def upgrade() -> None:
    bind = op.get_bind()

    op.add_column("goals", sa.Column("template", sa.String(length=50), nullable=True))

    intent_expr = "intent::text" if bind.dialect.name == "postgresql" else "intent"
    op.execute(
        f"""
        UPDATE goals
        SET template = CASE {intent_expr}
            WHEN 'GENERAL_SAVINGS' THEN 'general_savings'
            WHEN 'EMERGENCY_RESERVE' THEN 'emergency_fund'
            WHEN 'PURCHASE_ASSET' THEN 'asset_purchase'
            WHEN 'FUTURE_EXPENSE' THEN 'future_expense'
            WHEN 'PAY_DEBT' THEN 'debt'
            WHEN 'FUND_INSTALLMENT' THEN 'installment'
            WHEN 'FUND_PROJECT' THEN 'project'
            ELSE template
        END
        """
    )

    if bind.dialect.name == "postgresql":
        new_goal_intent = postgresql.ENUM(*NEW_INTENTS, name="goalintent_new")
        new_goal_intent.create(bind, checkfirst=True)

        op.execute("ALTER TABLE goals ALTER COLUMN intent DROP DEFAULT")
        op.execute(
            """
            ALTER TABLE goals
            ALTER COLUMN intent TYPE goalintent_new
            USING (
                CASE intent::text
                    WHEN 'GENERAL_SAVINGS' THEN 'RESERVE'
                    WHEN 'EMERGENCY_RESERVE' THEN 'RESERVE'
                    WHEN 'PURCHASE_ASSET' THEN 'PLANNED_PURCHASE'
                    WHEN 'FUTURE_EXPENSE' THEN 'PLANNED_PURCHASE'
                    WHEN 'PAY_DEBT' THEN 'PAY_OBLIGATION'
                    WHEN 'FUND_INSTALLMENT' THEN 'PAY_OBLIGATION'
                    WHEN 'FUND_PROJECT' THEN 'FUND_PROJECT'
                    ELSE 'RESERVE'
                END
            )::goalintent_new
            """
        )
        op.execute("DROP TYPE goalintent")
        op.execute("ALTER TYPE goalintent_new RENAME TO goalintent")
        op.execute("ALTER TABLE goals ALTER COLUMN intent SET DEFAULT 'RESERVE'")
    else:
        op.execute(
            """
            UPDATE goals
            SET intent = CASE intent
                WHEN 'GENERAL_SAVINGS' THEN 'RESERVE'
                WHEN 'EMERGENCY_RESERVE' THEN 'RESERVE'
                WHEN 'PURCHASE_ASSET' THEN 'PLANNED_PURCHASE'
                WHEN 'FUTURE_EXPENSE' THEN 'PLANNED_PURCHASE'
                WHEN 'PAY_DEBT' THEN 'PAY_OBLIGATION'
                WHEN 'FUND_INSTALLMENT' THEN 'PAY_OBLIGATION'
                WHEN 'FUND_PROJECT' THEN 'FUND_PROJECT'
                ELSE 'RESERVE'
            END
            """
        )


def downgrade() -> None:
    bind = op.get_bind()

    if bind.dialect.name == "postgresql":
        old_goal_intent = postgresql.ENUM(*OLD_INTENTS, name="goalintent_old")
        old_goal_intent.create(bind, checkfirst=True)

        op.execute("ALTER TABLE goals ALTER COLUMN intent DROP DEFAULT")
        op.execute(
            """
            ALTER TABLE goals
            ALTER COLUMN intent TYPE goalintent_old
            USING (
                CASE intent::text
                    WHEN 'RESERVE' THEN
                        CASE
                            WHEN template = 'emergency_fund' THEN 'EMERGENCY_RESERVE'
                            ELSE 'GENERAL_SAVINGS'
                        END
                    WHEN 'PLANNED_PURCHASE' THEN
                        CASE
                            WHEN template = 'asset_purchase' THEN 'PURCHASE_ASSET'
                            ELSE 'FUTURE_EXPENSE'
                        END
                    WHEN 'PAY_OBLIGATION' THEN
                        CASE
                            WHEN template = 'installment' THEN 'FUND_INSTALLMENT'
                            ELSE 'PAY_DEBT'
                        END
                    WHEN 'FUND_PROJECT' THEN 'FUND_PROJECT'
                    ELSE 'GENERAL_SAVINGS'
                END
            )::goalintent_old
            """
        )
        op.execute("DROP TYPE goalintent")
        op.execute("ALTER TYPE goalintent_old RENAME TO goalintent")
        op.execute("ALTER TABLE goals ALTER COLUMN intent SET DEFAULT 'GENERAL_SAVINGS'")
    else:
        op.execute(
            """
            UPDATE goals
            SET intent = CASE intent
                WHEN 'RESERVE' THEN
                    CASE
                        WHEN template = 'emergency_fund' THEN 'EMERGENCY_RESERVE'
                        ELSE 'GENERAL_SAVINGS'
                    END
                WHEN 'PLANNED_PURCHASE' THEN
                    CASE
                        WHEN template = 'asset_purchase' THEN 'PURCHASE_ASSET'
                        ELSE 'FUTURE_EXPENSE'
                    END
                WHEN 'PAY_OBLIGATION' THEN
                    CASE
                        WHEN template = 'installment' THEN 'FUND_INSTALLMENT'
                        ELSE 'PAY_DEBT'
                    END
                WHEN 'FUND_PROJECT' THEN 'FUND_PROJECT'
                ELSE 'GENERAL_SAVINGS'
            END
            """
        )

    op.drop_column("goals", "template")
