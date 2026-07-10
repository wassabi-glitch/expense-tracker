import os
import uuid
from pathlib import Path

import pytest
import sqlalchemy as sa
from alembic import command
from alembic.config import Config
from sqlalchemy.engine import make_url

from config import settings


PRE_DECOUPLING_REVISION = "a32b1c2d3e4f"
DECOUPLING_REVISION = "29e810b4fc08"


def _quote_ident(value: str) -> str:
    if not value.replace("_", "").isalnum():
        raise ValueError(f"Unsafe generated identifier: {value}")
    return f'"{value}"'


def _admin_url() -> str:
    url = make_url(settings.database_url)
    if not url.drivername.startswith("postgresql"):
        pytest.skip("Payment-plan migration tests require PostgreSQL")
    return url.set(database="postgres").render_as_string(hide_password=False)


@pytest.fixture()
def migration_db(monkeypatch):
    admin_engine = sa.create_engine(_admin_url(), isolation_level="AUTOCOMMIT")
    db_name = f"expense_tracker_migration_test_{os.getpid()}_{uuid.uuid4().hex[:8]}"
    quoted_db = _quote_ident(db_name)

    try:
        with admin_engine.connect() as conn:
            conn.execute(sa.text(f"CREATE DATABASE {quoted_db}"))
    except sa.exc.OperationalError as exc:
        pytest.skip(f"PostgreSQL migration test database is unavailable: {exc}")

    test_url = make_url(settings.database_url).set(database=db_name).render_as_string(hide_password=False)
    monkeypatch.setenv("DATABASE_URL", test_url)
    monkeypatch.setenv("ALEMBIC_USE_DATABASE_URL", "true")

    cfg = Config(str(Path(__file__).resolve().parents[1] / "alembic.ini"))
    command.upgrade(cfg, PRE_DECOUPLING_REVISION)

    engine = sa.create_engine(test_url)
    try:
        yield engine, cfg
    finally:
        engine.dispose()
        with admin_engine.connect() as conn:
            conn.execute(sa.text(f"DROP DATABASE IF EXISTS {quoted_db} WITH (FORCE)"))
        admin_engine.dispose()


def _seed_legacy_pristine_plan(conn):
    user_id = conn.execute(
        sa.text(
            """
            INSERT INTO users (
                email, username, hashed_password, is_verified, is_premium,
                timezone, total_debts_created
            )
            VALUES (
                'legacy-plan@example.com', 'legacyplan', 'hash', true, false,
                'UTC', 1
            )
            RETURNING id
            """
        )
    ).scalar_one()

    debt_id = conn.execute(
        sa.text(
            """
            INSERT INTO debts (
                owner_id, debt_type, origin_kind, counterparty_kind,
                counterparty_name, initial_amount, remaining_amount, currency,
                status, date, expected_return_date, is_money_transferred,
                expense_category
            )
            VALUES (
                :owner_id, 'OWING', 'FINANCED_ASSET_PURCHASE', 'STORE',
                'Phone Store', 900000, 900000, 'UZS',
                'ACTIVE', DATE '2026-01-01', DATE '2026-04-01', false,
                'ELECTRONICS'
            )
            RETURNING id
            """
        ),
        {"owner_id": user_id},
    ).scalar_one()

    conn.execute(
        sa.text(
            """
            INSERT INTO debt_ledger_entries (
                owner_id, debt_id, entry_type, amount_delta, principal_delta,
                charge_delta, balance_after, event_subtype, source,
                is_reversible, status, entry_date, note
            )
            VALUES (
                :owner_id, :debt_id, 'INITIAL', 900000, 900000,
                0, 900000, 'PAYMENT_PLAN_ORIGIN', 'SYSTEM',
                false, 'POSTED', DATE '2026-01-01',
                'Legacy payment-plan backing debt'
            )
            """
        ),
        {"owner_id": user_id, "debt_id": debt_id},
    )

    plan_id = conn.execute(
        sa.text(
            """
            INSERT INTO payment_plans (
                owner_id, debt_id, item_name, store_or_bank_name, plan_type,
                total_price, down_payment, remaining_amount, currency, months,
                payment_count, frequency, monthly_payment_amount,
                regular_payment_amount, schedule_rule, status, start_date,
                expense_category
            )
            VALUES (
                :owner_id, :debt_id, 'Phone', 'Phone Store',
                'STORE_INSTALLMENT', 900000, 0, 900000, 'UZS', 3,
                3, 'MONTHLY', 300000, 300000, '{"source":"LEGACY"}',
                'ACTIVE', DATE '2026-01-01', 'ELECTRONICS'
            )
            RETURNING id
            """
        ),
        {"owner_id": user_id, "debt_id": debt_id},
    ).scalar_one()

    payment_ids = []
    for month in range(1, 4):
        payment_id = conn.execute(
            sa.text(
                """
                INSERT INTO payment_plan_payments (
                    owner_id, plan_id, amount, paid_amount, written_off_amount,
                    component_type, status, due_date
                )
                VALUES (
                    :owner_id, :plan_id, 300000, 0, 0,
                    'PRINCIPAL', 'PENDING', :due_date
                )
                RETURNING id
                """
            ),
            {
                "owner_id": user_id,
                "plan_id": plan_id,
                "due_date": f"2026-0{month}-01",
            },
        ).scalar_one()
        payment_ids.append(payment_id)

    return {
        "user_id": user_id,
        "debt_id": debt_id,
        "plan_id": plan_id,
        "payment_ids": payment_ids,
    }


def _add_legacy_principal_payment(
    conn,
    ids,
    *,
    amount=300000,
    payment_status="PAID",
    balance_after=600000,
):
    wallet_balance_after = 1000000 - amount
    wallet_id = conn.execute(
        sa.text(
            """
            INSERT INTO wallets (
                owner_id, name, wallet_type, accounting_type, initial_balance,
                current_balance, overdraft_limit, has_overdraft, credit_limit,
                allow_overlimit, color, currency, can_fund_goals, is_default,
                is_active
            )
            VALUES (
                :owner_id, 'Cash', 'CASH', 'ASSET', 1000000, :wallet_balance_after,
                0, false, 0, false, 'default', 'UZS', false, true, true
            )
            RETURNING id
            """
        ),
        {"owner_id": ids["user_id"], "wallet_balance_after": wallet_balance_after},
    ).scalar_one()

    event_id = conn.execute(
        sa.text(
            """
            INSERT INTO financial_events (
                owner_id, title, event_type, status, reference_type,
                is_session, date
            )
            VALUES (
                :owner_id, 'Phone payment', 'EXPENSE', 'POSTED',
                'payment_plan_payment', false, DATE '2026-02-01'
            )
            RETURNING id
            """
        ),
        {"owner_id": ids["user_id"]},
    ).scalar_one()
    conn.execute(
        sa.text(
            """
            INSERT INTO wallet_ledger (owner_id, event_id, wallet_id, amount)
            VALUES (:owner_id, :event_id, :wallet_id, :wallet_delta)
            """
        ),
        {
            "owner_id": ids["user_id"],
            "event_id": event_id,
            "wallet_id": wallet_id,
            "wallet_delta": -amount,
        },
    )
    conn.execute(
        sa.text(
            """
            INSERT INTO entity_ledger (
                event_id, label, amount, category, debt_id
            )
            VALUES (
                :event_id, 'Phone payment', :amount, 'ELECTRONICS', :debt_id
            )
            """
        ),
        {"event_id": event_id, "debt_id": ids["debt_id"], "amount": amount},
    )

    debt_transaction_id = conn.execute(
        sa.text(
            """
            INSERT INTO debt_transactions (
                owner_id, wallet_id, debt_id, amount, date, note
            )
            VALUES (
                :owner_id, :wallet_id, :debt_id, :amount,
                DATE '2026-02-01', 'Legacy payment'
            )
            RETURNING id
            """
        ),
        {
            "owner_id": ids["user_id"],
            "wallet_id": wallet_id,
            "debt_id": ids["debt_id"],
            "amount": amount,
        },
    ).scalar_one()
    conn.execute(
        sa.text(
            """
            INSERT INTO debt_transaction_wallet_allocations (
                owner_id, debt_id, debt_transaction_id, wallet_id, amount
            )
            VALUES (
                :owner_id, :debt_id, :debt_transaction_id, :wallet_id, :amount
            )
            """
        ),
        {
            "owner_id": ids["user_id"],
            "debt_id": ids["debt_id"],
            "debt_transaction_id": debt_transaction_id,
            "wallet_id": wallet_id,
            "amount": amount,
        },
    )

    debt_ledger_entry_id = conn.execute(
        sa.text(
            """
            INSERT INTO debt_ledger_entries (
                owner_id, debt_id, financial_event_id,
                source_debt_transaction_id, wallet_id, entry_type,
                amount_delta, principal_delta, charge_delta, balance_after,
                event_subtype, source, is_reversible, status, entry_date, note
            )
            VALUES (
                :owner_id, :debt_id, :event_id, :debt_transaction_id,
                :wallet_id, 'PAYMENT', :amount_delta, :amount_delta, 0,
                :balance_after,
                'DEBT_REPAYMENT', 'USER', true, 'POSTED',
                DATE '2026-02-01', 'Legacy payment'
            )
            RETURNING id
            """
        ),
        {
            "owner_id": ids["user_id"],
            "debt_id": ids["debt_id"],
            "event_id": event_id,
            "debt_transaction_id": debt_transaction_id,
            "wallet_id": wallet_id,
            "amount_delta": -amount,
            "balance_after": balance_after,
        },
    ).scalar_one()

    payment_id = ids["payment_ids"][0]
    conn.execute(
        sa.text(
            """
            UPDATE payment_plan_payments
            SET
                paid_amount = :amount,
                status = :payment_status,
                paid_date = DATE '2026-02-01',
                event_id = :event_id,
                debt_ledger_entry_id = :debt_ledger_entry_id
            WHERE id = :payment_id
            """
        ),
        {
            "event_id": event_id,
            "debt_ledger_entry_id": debt_ledger_entry_id,
            "payment_id": payment_id,
            "amount": amount,
            "payment_status": payment_status,
        },
    )
    conn.execute(
        sa.text(
            """
            INSERT INTO payment_plan_payment_allocations (
                owner_id, payment_plan_payment_id, financial_event_id,
                debt_transaction_id, debt_ledger_entry_id, wallet_id,
                amount, paid_date, note
            )
            VALUES (
                :owner_id, :payment_id, :event_id, :debt_transaction_id,
                :debt_ledger_entry_id, :wallet_id, :amount,
                DATE '2026-02-01', 'Legacy payment'
            )
            """
        ),
        {
            "owner_id": ids["user_id"],
            "payment_id": payment_id,
            "event_id": event_id,
            "debt_transaction_id": debt_transaction_id,
            "debt_ledger_entry_id": debt_ledger_entry_id,
            "wallet_id": wallet_id,
            "amount": amount,
        },
    )
    conn.execute(
        sa.text("UPDATE debts SET remaining_amount = :balance_after WHERE id = :debt_id"),
        {"debt_id": ids["debt_id"], "balance_after": balance_after},
    )
    conn.execute(
        sa.text("UPDATE payment_plans SET remaining_amount = :balance_after WHERE id = :plan_id"),
        {"plan_id": ids["plan_id"], "balance_after": balance_after},
    )
    return {
        "wallet_id": wallet_id,
        "event_id": event_id,
        "debt_transaction_id": debt_transaction_id,
        "debt_ledger_entry_id": debt_ledger_entry_id,
        "payment_id": payment_id,
        "amount": amount,
        "balance_after": balance_after,
        "wallet_balance_after": wallet_balance_after,
        "payment_status": payment_status,
    }


def _add_legacy_full_payoff(conn, ids):
    wallet_id = conn.execute(
        sa.text(
            """
            INSERT INTO wallets (
                owner_id, name, wallet_type, accounting_type, initial_balance,
                current_balance, overdraft_limit, has_overdraft, credit_limit,
                allow_overlimit, color, currency, can_fund_goals, is_default,
                is_active
            )
            VALUES (
                :owner_id, 'Cash', 'CASH', 'ASSET', 1000000, 100000,
                0, false, 0, false, 'default', 'UZS', false, true, true
            )
            RETURNING id
            """
        ),
        {"owner_id": ids["user_id"]},
    ).scalar_one()
    event_id = conn.execute(
        sa.text(
            """
            INSERT INTO financial_events (
                owner_id, title, event_type, status, reference_type,
                is_session, date
            )
            VALUES (
                :owner_id, 'Phone payoff', 'EXPENSE', 'POSTED',
                'payment_plan_payment', false, DATE '2026-04-01'
            )
            RETURNING id
            """
        ),
        {"owner_id": ids["user_id"]},
    ).scalar_one()
    conn.execute(
        sa.text(
            """
            INSERT INTO wallet_ledger (owner_id, event_id, wallet_id, amount)
            VALUES (:owner_id, :event_id, :wallet_id, -900000)
            """
        ),
        {"owner_id": ids["user_id"], "event_id": event_id, "wallet_id": wallet_id},
    )
    debt_transaction_id = conn.execute(
        sa.text(
            """
            INSERT INTO debt_transactions (
                owner_id, wallet_id, debt_id, amount, date, note
            )
            VALUES (
                :owner_id, :wallet_id, :debt_id, 900000,
                DATE '2026-04-01', 'Legacy payoff'
            )
            RETURNING id
            """
        ),
        {
            "owner_id": ids["user_id"],
            "wallet_id": wallet_id,
            "debt_id": ids["debt_id"],
        },
    ).scalar_one()
    conn.execute(
        sa.text(
            """
            INSERT INTO debt_transaction_wallet_allocations (
                owner_id, debt_id, debt_transaction_id, wallet_id, amount
            )
            VALUES (
                :owner_id, :debt_id, :debt_transaction_id, :wallet_id, 900000
            )
            """
        ),
        {
            "owner_id": ids["user_id"],
            "debt_id": ids["debt_id"],
            "debt_transaction_id": debt_transaction_id,
            "wallet_id": wallet_id,
        },
    )
    debt_ledger_entry_id = conn.execute(
        sa.text(
            """
            INSERT INTO debt_ledger_entries (
                owner_id, debt_id, financial_event_id,
                source_debt_transaction_id, wallet_id, entry_type,
                amount_delta, principal_delta, charge_delta, balance_after,
                event_subtype, source, is_reversible, status, entry_date, note
            )
            VALUES (
                :owner_id, :debt_id, :event_id, :debt_transaction_id,
                :wallet_id, 'PAYMENT', -900000, -900000, 0, 0,
                'DEBT_REPAYMENT', 'USER', true, 'POSTED',
                DATE '2026-04-01', 'Legacy payoff'
            )
            RETURNING id
            """
        ),
        {
            "owner_id": ids["user_id"],
            "debt_id": ids["debt_id"],
            "event_id": event_id,
            "debt_transaction_id": debt_transaction_id,
            "wallet_id": wallet_id,
        },
    ).scalar_one()

    for payment_id in ids["payment_ids"]:
        conn.execute(
            sa.text(
                """
                UPDATE payment_plan_payments
                SET
                    paid_amount = 300000,
                    status = 'PAID',
                    paid_date = DATE '2026-04-01',
                    event_id = :event_id,
                    debt_ledger_entry_id = :debt_ledger_entry_id
                WHERE id = :payment_id
                """
            ),
            {
                "event_id": event_id,
                "debt_ledger_entry_id": debt_ledger_entry_id,
                "payment_id": payment_id,
            },
        )
        conn.execute(
            sa.text(
                """
                INSERT INTO payment_plan_payment_allocations (
                    owner_id, payment_plan_payment_id, financial_event_id,
                    debt_transaction_id, debt_ledger_entry_id, wallet_id,
                    amount, paid_date, note
                )
                VALUES (
                    :owner_id, :payment_id, :event_id, :debt_transaction_id,
                    :debt_ledger_entry_id, :wallet_id, 300000,
                    DATE '2026-04-01', 'Legacy payoff'
                )
                """
            ),
            {
                "owner_id": ids["user_id"],
                "payment_id": payment_id,
                "event_id": event_id,
                "debt_transaction_id": debt_transaction_id,
                "debt_ledger_entry_id": debt_ledger_entry_id,
                "wallet_id": wallet_id,
            },
        )

    conn.execute(
        sa.text("UPDATE debts SET remaining_amount = 0, status = 'PAID' WHERE id = :debt_id"),
        {"debt_id": ids["debt_id"]},
    )
    conn.execute(
        sa.text("UPDATE payment_plans SET remaining_amount = 0, status = 'PAID' WHERE id = :plan_id"),
        {"plan_id": ids["plan_id"]},
    )
    return {
        "wallet_id": wallet_id,
        "event_id": event_id,
        "debt_transaction_id": debt_transaction_id,
        "debt_ledger_entry_id": debt_ledger_entry_id,
    }


def _add_legacy_charge(conn, ids):
    charge_id = conn.execute(
        sa.text(
            """
            INSERT INTO debt_charges (
                owner_id, debt_id, amount, reason, date
            )
            VALUES (
                :owner_id, :debt_id, 50000, 'Late fee', DATE '2026-02-15'
            )
            RETURNING id
            """
        ),
        {"owner_id": ids["user_id"], "debt_id": ids["debt_id"]},
    ).scalar_one()

    charge_ledger_entry_id = conn.execute(
        sa.text(
            """
            INSERT INTO debt_ledger_entries (
                owner_id, debt_id, source_debt_charge_id, entry_type,
                amount_delta, principal_delta, charge_delta, balance_after,
                event_subtype, source, is_reversible, status, entry_date, note
            )
            VALUES (
                :owner_id, :debt_id, :charge_id, 'CHARGE',
                50000, 0, 50000, 950000, 'PAYMENT_PLAN_FEE',
                'USER', true, 'POSTED', DATE '2026-02-15', 'Late fee'
            )
            RETURNING id
            """
        ),
        {
            "owner_id": ids["user_id"],
            "debt_id": ids["debt_id"],
            "charge_id": charge_id,
        },
    ).scalar_one()

    charge_payment_id = conn.execute(
        sa.text(
            """
            INSERT INTO payment_plan_payments (
                owner_id, plan_id, debt_charge_id, amount, paid_amount,
                written_off_amount, component_type, status, due_date,
                note, debt_ledger_entry_id
            )
            VALUES (
                :owner_id, :plan_id, :charge_id, 50000, 0,
                0, 'CHARGE', 'PENDING', DATE '2026-02-15',
                'Late fee', :charge_ledger_entry_id
            )
            RETURNING id
            """
        ),
        {
            "owner_id": ids["user_id"],
            "plan_id": ids["plan_id"],
            "charge_id": charge_id,
            "charge_ledger_entry_id": charge_ledger_entry_id,
        },
    ).scalar_one()

    conn.execute(
        sa.text("UPDATE debts SET remaining_amount = 950000 WHERE id = :debt_id"),
        {"debt_id": ids["debt_id"]},
    )
    conn.execute(
        sa.text("UPDATE payment_plans SET remaining_amount = 950000 WHERE id = :plan_id"),
        {"plan_id": ids["plan_id"]},
    )
    return {
        "charge_id": charge_id,
        "charge_ledger_entry_id": charge_ledger_entry_id,
        "charge_payment_id": charge_payment_id,
    }


def _add_legacy_write_off(conn, ids):
    write_off_ledger_entry_id = conn.execute(
        sa.text(
            """
            INSERT INTO debt_ledger_entries (
                owner_id, debt_id, entry_type, amount_delta,
                principal_delta, charge_delta, balance_after, event_subtype,
                source, is_reversible, status, entry_date, note
            )
            VALUES (
                :owner_id, :debt_id, 'ADJUSTMENT', -300000,
                -300000, 0, 600000, 'PAYMENT_PLAN_WRITE_OFF',
                'USER', true, 'POSTED', DATE '2026-02-20',
                'Write-off for payment plan payment'
            )
            RETURNING id
            """
        ),
        {"owner_id": ids["user_id"], "debt_id": ids["debt_id"]},
    ).scalar_one()

    payment_id = ids["payment_ids"][0]
    conn.execute(
        sa.text(
            """
            UPDATE payment_plan_payments
            SET
                written_off_amount = 300000,
                status = 'PAID',
                paid_date = DATE '2026-02-20',
                debt_ledger_entry_id = :write_off_ledger_entry_id
            WHERE id = :payment_id
            """
        ),
        {
            "write_off_ledger_entry_id": write_off_ledger_entry_id,
            "payment_id": payment_id,
        },
    )
    conn.execute(
        sa.text("UPDATE debts SET remaining_amount = 600000 WHERE id = :debt_id"),
        {"debt_id": ids["debt_id"]},
    )
    conn.execute(
        sa.text("UPDATE payment_plans SET remaining_amount = 600000 WHERE id = :plan_id"),
        {"plan_id": ids["plan_id"]},
    )
    return {
        "write_off_ledger_entry_id": write_off_ledger_entry_id,
        "payment_id": payment_id,
    }


def _add_legacy_goal_targeting_backing_debt(conn, ids):
    return conn.execute(
        sa.text(
            """
            INSERT INTO goals (
                owner_id, title, target_amount, currency, intent, status,
                linked_debt_id
            )
            VALUES (
                :owner_id, 'Pay phone', 900000, 'UZS', 'PAY_OBLIGATION',
                'ACTIVE', :debt_id
            )
            RETURNING id
            """
        ),
        {"owner_id": ids["user_id"], "debt_id": ids["debt_id"]},
    ).scalar_one()


def _add_legacy_loan_disbursement(conn, ids):
    wallet_id = conn.execute(
        sa.text(
            """
            INSERT INTO wallets (
                owner_id, name, wallet_type, accounting_type, initial_balance,
                current_balance, overdraft_limit, has_overdraft, credit_limit,
                allow_overlimit, color, currency, can_fund_goals, is_default,
                is_active
            )
            VALUES (
                :owner_id, 'Debit', 'DEBIT', 'ASSET', 0, 900000,
                0, false, 0, false, 'default', 'UZS', false, true, true
            )
            RETURNING id
            """
        ),
        {"owner_id": ids["user_id"]},
    ).scalar_one()

    event_id = conn.execute(
        sa.text(
            """
            INSERT INTO financial_events (
                owner_id, title, event_type, status, reference_type,
                is_session, date
            )
            VALUES (
                :owner_id, 'Microloan disbursement', 'DEBT_SETTLEMENT',
                'POSTED', 'loan_disbursement', false, DATE '2026-01-01'
            )
            RETURNING id
            """
        ),
        {"owner_id": ids["user_id"]},
    ).scalar_one()
    conn.execute(
        sa.text(
            """
            INSERT INTO wallet_ledger (owner_id, event_id, wallet_id, amount)
            VALUES (:owner_id, :event_id, :wallet_id, 900000)
            """
        ),
        {"owner_id": ids["user_id"], "event_id": event_id, "wallet_id": wallet_id},
    )
    conn.execute(
        sa.text(
            """
            INSERT INTO entity_ledger (
                event_id, label, amount, debt_id
            )
            VALUES (
                :event_id, 'Microloan disbursement', 900000, :debt_id
            )
            """
        ),
        {"event_id": event_id, "debt_id": ids["debt_id"]},
    )
    conn.execute(
        sa.text(
            """
            UPDATE debts
            SET
                origin_kind = 'CASH_BORROWED',
                counterparty_kind = 'BANK',
                counterparty_name = 'Bank',
                is_money_transferred = true,
                linked_event_id = :event_id
            WHERE id = :debt_id
            """
        ),
        {"event_id": event_id, "debt_id": ids["debt_id"]},
    )
    conn.execute(
        sa.text(
            """
            UPDATE payment_plans
            SET plan_type = 'BANK_LOAN', store_or_bank_name = 'Bank'
            WHERE id = :plan_id
            """
        ),
        {"plan_id": ids["plan_id"]},
    )
    conn.execute(
        sa.text(
            """
            UPDATE debt_ledger_entries
            SET
                financial_event_id = :event_id,
                event_subtype = 'LOAN_DISBURSEMENT'
            WHERE debt_id = :debt_id
              AND entry_type = 'INITIAL'
            """
        ),
        {"event_id": event_id, "debt_id": ids["debt_id"]},
    )
    return {"wallet_id": wallet_id, "event_id": event_id}


def _add_real_user_debt(conn, owner_id):
    debt_id = conn.execute(
        sa.text(
            """
            INSERT INTO debts (
                owner_id, debt_type, origin_kind, counterparty_kind,
                counterparty_name, initial_amount, remaining_amount, currency,
                status, date, expected_return_date, is_money_transferred
            )
            VALUES (
                :owner_id, 'OWING', 'CASH_BORROWED', 'PERSON',
                'Friend', 123000, 123000, 'UZS',
                'ACTIVE', DATE '2026-01-05', DATE '2026-03-05', true
            )
            RETURNING id
            """
        ),
        {"owner_id": owner_id},
    ).scalar_one()
    conn.execute(
        sa.text(
            """
            INSERT INTO debt_ledger_entries (
                owner_id, debt_id, entry_type, amount_delta, principal_delta,
                charge_delta, balance_after, source, is_reversible, status,
                entry_date, note
            )
            VALUES (
                :owner_id, :debt_id, 'INITIAL', 123000, 123000,
                0, 123000, 'USER', true, 'POSTED',
                DATE '2026-01-05', 'Real user debt'
            )
            """
        ),
        {"owner_id": owner_id, "debt_id": debt_id},
    )
    goal_id = conn.execute(
        sa.text(
            """
            INSERT INTO goals (
                owner_id, title, target_amount, currency, intent, status,
                linked_debt_id
            )
            VALUES (
                :owner_id, 'Pay friend', 123000, 'UZS', 'PAY_OBLIGATION',
                'ACTIVE', :debt_id
            )
            RETURNING id
            """
        ),
        {"owner_id": owner_id, "debt_id": debt_id},
    ).scalar_one()
    return {"debt_id": debt_id, "goal_id": goal_id}


def _attach_legacy_plan_metadata(conn, ids):
    subcategory_id = conn.execute(
        sa.text(
            """
            INSERT INTO user_subcategories (
                owner_id, category, name, is_active, is_deleted
            )
            VALUES (
                :owner_id, 'ELECTRONICS', 'Phones', true, false
            )
            RETURNING id
            """
        ),
        {"owner_id": ids["user_id"]},
    ).scalar_one()
    project_id = conn.execute(
        sa.text(
            """
            INSERT INTO projects (
                owner_id, title, is_isolated, total_limit, status, start_date
            )
            VALUES (
                :owner_id, 'Upgrade setup', false, 2000000, 'ACTIVE',
                DATE '2026-01-01'
            )
            RETURNING id
            """
        ),
        {"owner_id": ids["user_id"]},
    ).scalar_one()
    project_subcategory_id = conn.execute(
        sa.text(
            """
            INSERT INTO project_subcategories (
                project_id, category, name, is_active, limit_amount
            )
            VALUES (
                :project_id, 'ELECTRONICS', 'Devices', true, 1500000
            )
            RETURNING id
            """
        ),
        {"project_id": project_id},
    ).scalar_one()
    asset_id = conn.execute(
        sa.text(
            """
            INSERT INTO assets (
                owner_id, title, purchase_value, current_value, status
            )
            VALUES (
                :owner_id, 'Phone asset', 900000, 800000, 'owned'
            )
            RETURNING id
            """
        ),
        {"owner_id": ids["user_id"]},
    ).scalar_one()
    conn.execute(
        sa.text(
            """
            UPDATE payment_plans
            SET
                expense_category = 'ELECTRONICS',
                expense_subcategory_id = :subcategory_id,
                project_id = :project_id,
                project_subcategory_id = :project_subcategory_id,
                asset_id = :asset_id
            WHERE id = :plan_id
            """
        ),
        {
            "plan_id": ids["plan_id"],
            "subcategory_id": subcategory_id,
            "project_id": project_id,
            "project_subcategory_id": project_subcategory_id,
            "asset_id": asset_id,
        },
    )
    return {
        "subcategory_id": subcategory_id,
        "project_id": project_id,
        "project_subcategory_id": project_subcategory_id,
        "asset_id": asset_id,
    }


def test_pristine_legacy_payment_plan_gets_plan_owned_initial_history(migration_db):
    engine, cfg = migration_db
    with engine.begin() as conn:
        ids = _seed_legacy_pristine_plan(conn)

    command.upgrade(cfg, DECOUPLING_REVISION)

    with engine.connect() as conn:
        plan = conn.execute(
            sa.text("SELECT debt_id, remaining_amount FROM payment_plans WHERE id = :plan_id"),
            {"plan_id": ids["plan_id"]},
        ).mappings().one()
        assert plan["debt_id"] is None
        assert plan["remaining_amount"] == 900000

        entries = conn.execute(
            sa.text(
                """
                SELECT entry_type, amount_delta, principal_delta, charge_delta,
                       balance_after, event_subtype, source
                FROM payment_plan_ledger_entries
                WHERE plan_id = :plan_id
                ORDER BY entry_date, id
                """
            ),
            {"plan_id": ids["plan_id"]},
        ).mappings().all()
        assert entries == [
            {
                "entry_type": "INITIAL",
                "amount_delta": 900000,
                "principal_delta": 900000,
                "charge_delta": 0,
                "balance_after": 900000,
                "event_subtype": "PAYMENT_PLAN_ORIGIN",
                "source": "SYSTEM",
            }
        ]

        backing_debt = conn.execute(
            sa.text("SELECT status, archived_at FROM debts WHERE id = :debt_id"),
            {"debt_id": ids["debt_id"]},
        ).mappings().one()
        assert backing_debt["status"] == "ARCHIVED"
        assert backing_debt["archived_at"] is not None


def test_decoupling_migration_downgrade_restores_legacy_schema_columns(migration_db):
    engine, cfg = migration_db

    command.upgrade(cfg, DECOUPLING_REVISION)
    command.downgrade(cfg, PRE_DECOUPLING_REVISION)

    with engine.connect() as conn:
        allocation_columns = {
            row["column_name"]
            for row in conn.execute(
                sa.text(
                    """
                    SELECT column_name
                    FROM information_schema.columns
                    WHERE table_name = 'payment_plan_payment_allocations'
                    """
                )
            ).mappings()
        }
        assert {"wallet_id", "debt_transaction_id", "debt_ledger_entry_id"}.issubset(allocation_columns)
        assert "payment_plan_transaction_id" not in allocation_columns
        assert "payment_plan_ledger_entry_id" not in allocation_columns

        payment_columns = {
            row["column_name"]
            for row in conn.execute(
                sa.text(
                    """
                    SELECT column_name
                    FROM information_schema.columns
                    WHERE table_name = 'payment_plan_payments'
                    """
                )
            ).mappings()
        }
        assert {"debt_charge_id", "debt_ledger_entry_id"}.issubset(payment_columns)
        assert "payment_plan_charge_id" not in payment_columns
        assert "payment_plan_ledger_entry_id" not in payment_columns

        plan_owned_tables = conn.execute(
            sa.text(
                """
                SELECT table_name
                FROM information_schema.tables
                WHERE table_schema = 'public'
                  AND table_name IN (
                    'payment_plan_charges',
                    'payment_plan_transactions',
                    'payment_plan_ledger_entries',
                    'payment_plan_transaction_wallet_allocations'
                  )
                """
            )
        ).scalars().all()
        assert plan_owned_tables == []


def test_legacy_payment_history_moves_to_plan_owned_accounting(migration_db):
    engine, cfg = migration_db
    with engine.begin() as conn:
        ids = _seed_legacy_pristine_plan(conn)
        payment_ids = _add_legacy_principal_payment(conn, ids)

    command.upgrade(cfg, DECOUPLING_REVISION)

    with engine.connect() as conn:
        wallet_balance = conn.execute(
            sa.text("SELECT current_balance FROM wallets WHERE id = :wallet_id"),
            {"wallet_id": payment_ids["wallet_id"]},
        ).scalar_one()
        assert wallet_balance == 700000

        entries = conn.execute(
            sa.text(
                """
                SELECT id, financial_event_id, source_transaction_id,
                       entry_type, amount_delta, principal_delta, charge_delta,
                       balance_after, event_subtype, source
                FROM payment_plan_ledger_entries
                WHERE plan_id = :plan_id
                ORDER BY entry_date, id
                """
            ),
            {"plan_id": ids["plan_id"]},
        ).mappings().all()
        assert [entry["entry_type"] for entry in entries] == ["INITIAL", "PAYMENT"]
        payment_entry = entries[1]
        assert payment_entry["financial_event_id"] == payment_ids["event_id"]
        assert payment_entry["amount_delta"] == -300000
        assert payment_entry["principal_delta"] == -300000
        assert payment_entry["charge_delta"] == 0
        assert payment_entry["balance_after"] == 600000
        assert payment_entry["event_subtype"] == "DEBT_REPAYMENT"
        assert payment_entry["source"] == "SYSTEM"

        transaction = conn.execute(
            sa.text(
                """
                SELECT id, amount, date, note
                FROM payment_plan_transactions
                WHERE plan_id = :plan_id
                """
            ),
            {"plan_id": ids["plan_id"]},
        ).mappings().one()
        assert transaction["amount"] == 300000
        assert str(transaction["date"]) == "2026-02-01"
        assert transaction["note"] == "Legacy payment"

        wallet_allocation = conn.execute(
            sa.text(
                """
                SELECT wallet_id, amount
                FROM payment_plan_transaction_wallet_allocations
                WHERE payment_plan_transaction_id = :transaction_id
                """
            ),
            {"transaction_id": transaction["id"]},
        ).mappings().one()
        assert wallet_allocation == {
            "wallet_id": payment_ids["wallet_id"],
            "amount": 300000,
        }

        schedule_payment = conn.execute(
            sa.text(
                """
                SELECT paid_amount, status, event_id, payment_plan_ledger_entry_id
                FROM payment_plan_payments
                WHERE id = :payment_id
                """
            ),
            {"payment_id": payment_ids["payment_id"]},
        ).mappings().one()
        assert schedule_payment == {
            "paid_amount": 300000,
            "status": "PAID",
            "event_id": payment_ids["event_id"],
            "payment_plan_ledger_entry_id": payment_entry["id"],
        }

        schedule_allocation = conn.execute(
            sa.text(
                """
                SELECT financial_event_id, payment_plan_transaction_id,
                       payment_plan_ledger_entry_id, amount
                FROM payment_plan_payment_allocations
                WHERE payment_plan_payment_id = :payment_id
                """
            ),
            {"payment_id": payment_ids["payment_id"]},
        ).mappings().one()
        assert schedule_allocation == {
            "financial_event_id": payment_ids["event_id"],
            "payment_plan_transaction_id": transaction["id"],
            "payment_plan_ledger_entry_id": payment_entry["id"],
            "amount": 300000,
        }

        event_trace = conn.execute(
            sa.text(
                """
                SELECT debt_id, payment_plan_id, payment_plan_payment_id
                FROM entity_ledger
                WHERE event_id = :event_id
                """
            ),
            {"event_id": payment_ids["event_id"]},
        ).mappings().one()
        assert event_trace == {
            "debt_id": None,
            "payment_plan_id": ids["plan_id"],
            "payment_plan_payment_id": payment_ids["payment_id"],
        }


def test_partially_paid_legacy_plan_keeps_partial_schedule_state(migration_db):
    engine, cfg = migration_db
    with engine.begin() as conn:
        ids = _seed_legacy_pristine_plan(conn)
        payment_ids = _add_legacy_principal_payment(
            conn,
            ids,
            amount=200000,
            payment_status="PARTIAL",
            balance_after=700000,
        )

    command.upgrade(cfg, DECOUPLING_REVISION)

    with engine.connect() as conn:
        plan_remaining = conn.execute(
            sa.text("SELECT remaining_amount FROM payment_plans WHERE id = :plan_id"),
            {"plan_id": ids["plan_id"]},
        ).scalar_one()
        assert plan_remaining == 700000

        payment_entry = conn.execute(
            sa.text(
                """
                SELECT id, source_transaction_id, amount_delta,
                       principal_delta, balance_after
                FROM payment_plan_ledger_entries
                WHERE plan_id = :plan_id AND entry_type = 'PAYMENT'
                """
            ),
            {"plan_id": ids["plan_id"]},
        ).mappings().one()
        assert payment_entry["amount_delta"] == -200000
        assert payment_entry["principal_delta"] == -200000
        assert payment_entry["balance_after"] == 700000

        transaction = conn.execute(
            sa.text(
                """
                SELECT amount
                FROM payment_plan_transactions
                WHERE id = :transaction_id
                """
            ),
            {"transaction_id": payment_entry["source_transaction_id"]},
        ).scalar_one()
        assert transaction == 200000

        schedule_payment = conn.execute(
            sa.text(
                """
                SELECT paid_amount, written_off_amount, status,
                       payment_plan_ledger_entry_id
                FROM payment_plan_payments
                WHERE id = :payment_id
                """
            ),
            {"payment_id": payment_ids["payment_id"]},
        ).mappings().one()
        assert schedule_payment == {
            "paid_amount": 200000,
            "written_off_amount": 0,
            "status": "PARTIAL",
            "payment_plan_ledger_entry_id": payment_entry["id"],
        }

        schedule_allocation_amount = conn.execute(
            sa.text(
                """
                SELECT amount
                FROM payment_plan_payment_allocations
                WHERE payment_plan_payment_id = :payment_id
                """
            ),
            {"payment_id": payment_ids["payment_id"]},
        ).scalar_one()
        assert schedule_allocation_amount == 200000


def test_fully_paid_legacy_plan_keeps_closed_balance_and_schedule(migration_db):
    engine, cfg = migration_db
    with engine.begin() as conn:
        ids = _seed_legacy_pristine_plan(conn)
        payoff_ids = _add_legacy_full_payoff(conn, ids)

    command.upgrade(cfg, DECOUPLING_REVISION)

    with engine.connect() as conn:
        plan = conn.execute(
            sa.text("SELECT status, remaining_amount FROM payment_plans WHERE id = :plan_id"),
            {"plan_id": ids["plan_id"]},
        ).mappings().one()
        assert plan == {"status": "PAID", "remaining_amount": 0}

        paid_schedule = conn.execute(
            sa.text(
                """
                SELECT count(*), sum(paid_amount), sum(written_off_amount)
                FROM payment_plan_payments
                WHERE plan_id = :plan_id AND status = 'PAID'
                """
            ),
            {"plan_id": ids["plan_id"]},
        ).one()
        assert paid_schedule == (3, 900000, 0)

        ledger_payment = conn.execute(
            sa.text(
                """
                SELECT source_transaction_id, amount_delta, principal_delta,
                       balance_after
                FROM payment_plan_ledger_entries
                WHERE plan_id = :plan_id AND entry_type = 'PAYMENT'
                """
            ),
            {"plan_id": ids["plan_id"]},
        ).mappings().one()
        assert ledger_payment["amount_delta"] == -900000
        assert ledger_payment["principal_delta"] == -900000
        assert ledger_payment["balance_after"] == 0

        transaction_amount = conn.execute(
            sa.text(
                """
                SELECT amount
                FROM payment_plan_transactions
                WHERE id = :transaction_id
                """
            ),
            {"transaction_id": ledger_payment["source_transaction_id"]},
        ).scalar_one()
        assert transaction_amount == 900000

        wallet_balance = conn.execute(
            sa.text("SELECT current_balance FROM wallets WHERE id = :wallet_id"),
            {"wallet_id": payoff_ids["wallet_id"]},
        ).scalar_one()
        assert wallet_balance == 100000


def test_legacy_charge_history_moves_to_plan_owned_accounting(migration_db):
    engine, cfg = migration_db
    with engine.begin() as conn:
        ids = _seed_legacy_pristine_plan(conn)
        charge_ids = _add_legacy_charge(conn, ids)

    command.upgrade(cfg, DECOUPLING_REVISION)

    with engine.connect() as conn:
        plan_remaining = conn.execute(
            sa.text("SELECT remaining_amount FROM payment_plans WHERE id = :plan_id"),
            {"plan_id": ids["plan_id"]},
        ).scalar_one()
        assert plan_remaining == 950000

        charge = conn.execute(
            sa.text(
                """
                SELECT id, amount, reason, date
                FROM payment_plan_charges
                WHERE plan_id = :plan_id
                """
            ),
            {"plan_id": ids["plan_id"]},
        ).mappings().one()
        assert charge["amount"] == 50000
        assert charge["reason"] == "Late fee"
        assert str(charge["date"]) == "2026-02-15"

        entries = conn.execute(
            sa.text(
                """
                SELECT source_charge_id, entry_type, amount_delta,
                       principal_delta, charge_delta, balance_after,
                       event_subtype, source
                FROM payment_plan_ledger_entries
                WHERE plan_id = :plan_id
                ORDER BY entry_date, id
                """
            ),
            {"plan_id": ids["plan_id"]},
        ).mappings().all()
        assert [entry["entry_type"] for entry in entries] == ["INITIAL", "CHARGE"]
        charge_entry = entries[1]
        assert charge_entry == {
            "source_charge_id": charge["id"],
            "entry_type": "CHARGE",
            "amount_delta": 50000,
            "principal_delta": 0,
            "charge_delta": 50000,
            "balance_after": 950000,
            "event_subtype": "PAYMENT_PLAN_FEE",
            "source": "SYSTEM",
        }

        charge_payment = conn.execute(
            sa.text(
                """
                SELECT payment_plan_charge_id, component_type, amount, status
                FROM payment_plan_payments
                WHERE id = :payment_id
                """
            ),
            {"payment_id": charge_ids["charge_payment_id"]},
        ).mappings().one()
        assert charge_payment == {
            "payment_plan_charge_id": charge["id"],
            "component_type": "CHARGE",
            "amount": 50000,
            "status": "PENDING",
        }


def test_legacy_write_off_history_moves_to_plan_owned_accounting(migration_db):
    engine, cfg = migration_db
    with engine.begin() as conn:
        ids = _seed_legacy_pristine_plan(conn)
        write_off_ids = _add_legacy_write_off(conn, ids)

    command.upgrade(cfg, DECOUPLING_REVISION)

    with engine.connect() as conn:
        entries = conn.execute(
            sa.text(
                """
                SELECT id, source_transaction_id, entry_type, amount_delta,
                       principal_delta, charge_delta, balance_after,
                       event_subtype, source
                FROM payment_plan_ledger_entries
                WHERE plan_id = :plan_id
                ORDER BY entry_date, id
                """
            ),
            {"plan_id": ids["plan_id"]},
        ).mappings().all()
        assert [entry["entry_type"] for entry in entries] == ["INITIAL", "ADJUSTMENT"]
        write_off_entry = entries[1]
        assert write_off_entry["source_transaction_id"] is not None
        assert write_off_entry["amount_delta"] == -300000
        assert write_off_entry["principal_delta"] == -300000
        assert write_off_entry["charge_delta"] == 0
        assert write_off_entry["balance_after"] == 600000
        assert write_off_entry["event_subtype"] == "PAYMENT_PLAN_WRITE_OFF"
        assert write_off_entry["source"] == "SYSTEM"

        transaction = conn.execute(
            sa.text(
                """
                SELECT amount, date, note
                FROM payment_plan_transactions
                WHERE id = :transaction_id
                """
            ),
            {"transaction_id": write_off_entry["source_transaction_id"]},
        ).mappings().one()
        assert transaction["amount"] == 300000
        assert str(transaction["date"]) == "2026-02-20"
        assert transaction["note"] == "Write-off for payment plan payment"

        wallet_allocation_count = conn.execute(
            sa.text(
                """
                SELECT count(*)
                FROM payment_plan_transaction_wallet_allocations
                WHERE payment_plan_transaction_id = :transaction_id
                """
            ),
            {"transaction_id": write_off_entry["source_transaction_id"]},
        ).scalar_one()
        assert wallet_allocation_count == 0

        schedule_payment = conn.execute(
            sa.text(
                """
                SELECT paid_amount, written_off_amount, status,
                       payment_plan_ledger_entry_id
                FROM payment_plan_payments
                WHERE id = :payment_id
                """
            ),
            {"payment_id": write_off_ids["payment_id"]},
        ).mappings().one()
        assert schedule_payment == {
            "paid_amount": 0,
            "written_off_amount": 300000,
            "status": "PAID",
            "payment_plan_ledger_entry_id": write_off_entry["id"],
        }


def test_goal_targeting_legacy_backing_debt_targets_payment_plan_after_migration(migration_db):
    engine, cfg = migration_db
    with engine.begin() as conn:
        ids = _seed_legacy_pristine_plan(conn)
        goal_id = _add_legacy_goal_targeting_backing_debt(conn, ids)

    command.upgrade(cfg, DECOUPLING_REVISION)

    with engine.connect() as conn:
        goal = conn.execute(
            sa.text(
                """
                SELECT linked_debt_id, linked_payment_plan_id
                FROM goals
                WHERE id = :goal_id
                """
            ),
            {"goal_id": goal_id},
        ).mappings().one()
        assert goal == {
            "linked_debt_id": None,
            "linked_payment_plan_id": ids["plan_id"],
        }


def test_bank_loan_disbursement_history_stays_traceable_to_payment_plan(migration_db):
    engine, cfg = migration_db
    with engine.begin() as conn:
        ids = _seed_legacy_pristine_plan(conn)
        disbursement_ids = _add_legacy_loan_disbursement(conn, ids)

    command.upgrade(cfg, DECOUPLING_REVISION)

    with engine.connect() as conn:
        wallet_balance = conn.execute(
            sa.text("SELECT current_balance FROM wallets WHERE id = :wallet_id"),
            {"wallet_id": disbursement_ids["wallet_id"]},
        ).scalar_one()
        assert wallet_balance == 900000

        opening = conn.execute(
            sa.text(
                """
                SELECT financial_event_id, entry_type, amount_delta,
                       principal_delta, balance_after, event_subtype
                FROM payment_plan_ledger_entries
                WHERE plan_id = :plan_id
                """
            ),
            {"plan_id": ids["plan_id"]},
        ).mappings().one()
        assert opening == {
            "financial_event_id": disbursement_ids["event_id"],
            "entry_type": "INITIAL",
            "amount_delta": 900000,
            "principal_delta": 900000,
            "balance_after": 900000,
            "event_subtype": "LOAN_DISBURSEMENT",
        }

        event_trace = conn.execute(
            sa.text(
                """
                SELECT debt_id, payment_plan_id
                FROM entity_ledger
                WHERE event_id = :event_id
                """
            ),
            {"event_id": disbursement_ids["event_id"]},
        ).mappings().one()
        assert event_trace == {
            "debt_id": None,
            "payment_plan_id": ids["plan_id"],
        }


def test_real_user_debt_is_not_retired_or_retargeted(migration_db):
    engine, cfg = migration_db
    with engine.begin() as conn:
        ids = _seed_legacy_pristine_plan(conn)
        real_debt = _add_real_user_debt(conn, ids["user_id"])

    command.upgrade(cfg, DECOUPLING_REVISION)

    with engine.connect() as conn:
        debt = conn.execute(
            sa.text(
                """
                SELECT status, archived_at, remaining_amount
                FROM debts
                WHERE id = :debt_id
                """
            ),
            {"debt_id": real_debt["debt_id"]},
        ).mappings().one()
        assert debt == {
            "status": "ACTIVE",
            "archived_at": None,
            "remaining_amount": 123000,
        }

        goal = conn.execute(
            sa.text(
                """
                SELECT linked_debt_id, linked_payment_plan_id
                FROM goals
                WHERE id = :goal_id
                """
            ),
            {"goal_id": real_debt["goal_id"]},
        ).mappings().one()
        assert goal == {
            "linked_debt_id": real_debt["debt_id"],
            "linked_payment_plan_id": None,
        }


def test_plan_metadata_links_survive_backing_debt_migration(migration_db):
    engine, cfg = migration_db
    with engine.begin() as conn:
        ids = _seed_legacy_pristine_plan(conn)
        metadata_ids = _attach_legacy_plan_metadata(conn, ids)

    command.upgrade(cfg, DECOUPLING_REVISION)

    with engine.connect() as conn:
        plan_links = conn.execute(
            sa.text(
                """
                SELECT expense_category, expense_subcategory_id, project_id,
                       project_subcategory_id, asset_id
                FROM payment_plans
                WHERE id = :plan_id
                """
            ),
            {"plan_id": ids["plan_id"]},
        ).mappings().one()
        assert plan_links == {
            "expense_category": "ELECTRONICS",
            "expense_subcategory_id": metadata_ids["subcategory_id"],
            "project_id": metadata_ids["project_id"],
            "project_subcategory_id": metadata_ids["project_subcategory_id"],
            "asset_id": metadata_ids["asset_id"],
        }
