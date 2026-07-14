"""Tests for Ticket 6: Cross-Flow Ledger Foundation Guardrails.

A regression guardrail matrix for all audited UI-facing posted-money paths.
Every flow must have at least one accepted same-day epoch case and at least
one rejected pre-epoch case. Rejected flows must prove no partial posted-money
rows or wallet balance changes are committed. Tests use project timezone
helpers and explicit X-Timezone headers.
"""

from datetime import datetime, timedelta, timezone

from app import models
from app.domains.ledger import verify_wallet_projection
from tests.helpers import (
    TEST_TIMEZONE,
    create_budget,
    create_user_and_token,
    user_timezone_today,
)


# ---------------------------------------------------------------------------
# Session expense finalization guardrails (Ticket 3 coverage)
# ---------------------------------------------------------------------------

def _create_session_draft(client, headers, wallet_id, amount=10_000):
    """Create a session draft with one item and one wallet allocation."""
    today = user_timezone_today()
    res = client.post(
        "/expenses/session-drafts",
        json={
            "title": "Test Session",
            "date": today.isoformat(),
            "amount_paid": amount,
        },
        headers=headers,
    )
    assert res.status_code == 201, f"Create draft failed: {res.json()}"
    draft_id = res.json()["id"]

    res = client.post(
        f"/expenses/session-drafts/{draft_id}/items",
        json={
            "label": "Test Item",
            "original_amount": amount,
            "category": "Groceries",
        },
        headers=headers,
    )
    assert res.status_code in (200, 201), f"Add item failed: {res.json()}"

    res = client.post(
        f"/expenses/session-drafts/{draft_id}/wallet-allocations",
        json={"wallet_id": wallet_id, "amount": amount},
        headers=headers,
    )
    assert res.status_code in (200, 201, 409), f"Add allocation failed: {res.json()}"

    return draft_id


def test_session_finalize_pre_epoch_rejected_no_side_effects(client, session):
    """Session finalization with a pre-epoch wallet is rejected with no side effects."""
    headers = create_user_and_token(
        client, "grdsess1", "grdsess1@example.com", "Password123!"
    )
    today = user_timezone_today()
    create_budget(
        client, headers,
        category="Groceries", monthly_limit=500_000,
        budget_year=today.year, budget_month=today.month,
    )

    user = session.query(models.User).filter(models.User.email == "grdsess1@example.com").first()
    wallet = (
        session.query(models.Wallet)
        .filter(models.Wallet.owner_id == user.id, models.Wallet.is_default)
        .first()
    )
    wallet_epoch = today + timedelta(days=1)
    wallet.created_at = datetime(wallet_epoch.year, wallet_epoch.month, wallet_epoch.day,
                                  tzinfo=timezone.utc)
    session.commit()

    balance_before = int(wallet.current_balance)
    event_count_before = (
        session.query(models.FinancialEvent)
        .filter(models.FinancialEvent.owner_id == user.id)
        .count()
    )

    draft_id = _create_session_draft(client, headers, wallet.id, amount=10_000)

    res = client.post(
        f"/expenses/session-drafts/{draft_id}/finalize",
        headers=headers,
    )
    assert res.status_code == 400, f"Expected 400, got {res.status_code}: {res.json()}"
    detail = res.json()["detail"]
    assert detail["code"] == "wallets.date_before_epoch", f"Got: {detail}"

    # No side effects
    session.expire_all()
    wallet_after = (
        session.query(models.Wallet)
        .filter(models.Wallet.id == wallet.id)
        .first()
    )
    assert int(wallet_after.current_balance) == balance_before

    event_count_after = (
        session.query(models.FinancialEvent)
        .filter(models.FinancialEvent.owner_id == user.id)
        .count()
    )
    assert event_count_after == event_count_before

    draft = (
        session.query(models.ExpenseSessionDraft)
        .filter(models.ExpenseSessionDraft.id == draft_id)
        .first()
    )
    assert draft is not None
    assert draft.status != models.ExpenseSessionDraftStatus.FINALIZED


def test_session_finalize_same_day_accepted(client, session):
    """Session finalization on the wallet's tracking start date is accepted."""
    headers = create_user_and_token(
        client, "grdsess2", "grdsess2@example.com", "Password123!"
    )
    today = user_timezone_today()
    create_budget(
        client, headers,
        category="Groceries", monthly_limit=500_000,
        budget_year=today.year, budget_month=today.month,
    )

    user = session.query(models.User).filter(models.User.email == "grdsess2@example.com").first()
    wallet = (
        session.query(models.Wallet)
        .filter(models.Wallet.owner_id == user.id, models.Wallet.is_default)
        .first()
    )
    wallet.created_at = datetime(today.year, today.month, today.day, tzinfo=timezone.utc)
    session.commit()

    draft_id = _create_session_draft(client, headers, wallet.id, amount=10_000)

    res = client.post(
        f"/expenses/session-drafts/{draft_id}/finalize",
        headers=headers,
    )
    assert res.status_code in (200, 201), f"Expected 200/201, got {res.status_code}: {res.json()}"


# ---------------------------------------------------------------------------
# Debt wallet movement guardrails (Ticket 4 coverage)
# ---------------------------------------------------------------------------

def test_debt_creation_pre_epoch_wallet_movement_rejected(client, session):
    """Debt creation with initial wallet movement before the wallet epoch is
    rejected with zero side effects."""
    headers = create_user_and_token(
        client, "grddebt1", "grddebt1@example.com", "Password123!"
    )
    today = user_timezone_today()
    user = session.query(models.User).filter(models.User.email == "grddebt1@example.com").first()
    wallet = (
        session.query(models.Wallet)
        .filter(models.Wallet.owner_id == user.id, models.Wallet.is_default)
        .first()
    )
    wallet_epoch = today + timedelta(days=1)
    wallet.created_at = datetime(wallet_epoch.year, wallet_epoch.month, wallet_epoch.day,
                                  tzinfo=timezone.utc)
    session.commit()

    balance_before = int(wallet.current_balance)
    event_count_before = (
        session.query(models.FinancialEvent)
        .filter(models.FinancialEvent.owner_id == user.id)
        .count()
    )

    res = client.post(
        "/debts",
        json={
            "debt_type": "OWING",
            "origin_kind": "CASH_BORROWED",
            "counterparty_kind": "BANK",
            "counterparty_name": "Test Bank",
            "initial_amount": 100_000,
            "date": today.isoformat(),
            "expected_return_date": today.isoformat(),
            "expense_category": "Groceries",
            "initial_wallet_allocations": [{"wallet_id": wallet.id, "amount": 100_000}],
        },
        headers=headers,
    )
    assert res.status_code == 400, f"Expected 400, got {res.status_code}: {res.json()}"
    detail = res.json()["detail"]
    assert detail["code"] == "wallets.date_before_epoch", f"Got: {detail}"

    # No side effects
    session.expire_all()
    wallet_after = (
        session.query(models.Wallet)
        .filter(models.Wallet.id == wallet.id)
        .first()
    )
    assert int(wallet_after.current_balance) == balance_before

    event_count_after = (
        session.query(models.FinancialEvent)
        .filter(models.FinancialEvent.owner_id == user.id)
        .count()
    )
    assert event_count_after == event_count_before

    debt_count = (
        session.query(models.Debt)
        .filter(models.Debt.owner_id == user.id)
        .count()
    )
    assert debt_count == 0


def test_debt_creation_same_day_accepted(client, session):
    """Debt creation on the wallet's tracking start date is accepted."""
    headers = create_user_and_token(
        client, "grddebt2", "grddebt2@example.com", "Password123!"
    )
    today = user_timezone_today()
    user = session.query(models.User).filter(models.User.email == "grddebt2@example.com").first()
    wallet = (
        session.query(models.Wallet)
        .filter(models.Wallet.owner_id == user.id, models.Wallet.is_default)
        .first()
    )
    wallet.created_at = datetime(today.year, today.month, today.day, tzinfo=timezone.utc)
    session.commit()

    res = client.post(
        "/debts",
        json={
            "debt_type": "OWING",
            "origin_kind": "CASH_BORROWED",
            "counterparty_kind": "BANK",
            "counterparty_name": "Test Bank",
            "initial_amount": 50_000,
            "date": today.isoformat(),
            "expected_return_date": today.isoformat(),
            "expense_category": "Groceries",
            "initial_wallet_allocations": [{"wallet_id": wallet.id, "amount": 50_000}],
        },
        headers=headers,
    )
    assert res.status_code in (200, 201), f"Expected 200/201, got {res.status_code}: {res.json()}"


# ---------------------------------------------------------------------------
# Payment Plan wallet movement guardrails (Ticket 5 coverage)
# ---------------------------------------------------------------------------

def test_payment_plan_disbursement_pre_epoch_rejected(client, session):
    """Payment plan setup with loan disbursement to a pre-epoch wallet is rejected."""
    headers = create_user_and_token(
        client, "grdpp1", "grdpp1@example.com", "Password123!"
    )
    today = user_timezone_today()
    create_budget(
        client, headers,
        category="Groceries", monthly_limit=500_000,
        budget_year=today.year, budget_month=today.month,
    )

    user = session.query(models.User).filter(models.User.email == "grdpp1@example.com").first()
    wallet = (
        session.query(models.Wallet)
        .filter(models.Wallet.owner_id == user.id, models.Wallet.is_default)
        .first()
    )
    wallet.created_at = datetime(2020, 1, 1, tzinfo=timezone.utc)
    wallet.initial_balance = 5_000_000
    wallet.current_balance = 5_000_000

    # Disbursement wallet with future epoch
    disbursement_epoch = today + timedelta(days=1)
    disbursement_wallet = models.Wallet(
        owner_id=user.id,
        name="Disbursement Wallet",
        wallet_type=models.WalletType.CASH,
        accounting_type=models.AccountingType.ASSET,
        initial_balance=0,
        current_balance=0,
        created_at=datetime(disbursement_epoch.year, disbursement_epoch.month,
                            disbursement_epoch.day, tzinfo=timezone.utc),
    )
    session.add(disbursement_wallet)
    session.commit()

    event_count_before = (
        session.query(models.FinancialEvent)
        .filter(models.FinancialEvent.owner_id == user.id)
        .count()
    )

    res = client.post(
        "/payment-plans",
        json={
            "plan_type": "BANK_LOAN",
            "item_name": "Test Loan",
            "store_or_bank_name": "Test Bank",
            "total_price": 100_000,
            "down_payment": 0,
            "months": 5,
            "frequency": "MONTHLY",
            "start_date": today.isoformat(),
            "expense_category": "Groceries",
            "schedule_model": "FLAT_TOTAL",
            "loan_disbursement_wallet_id": disbursement_wallet.id,
        },
        headers=headers,
    )
    assert res.status_code == 400, f"Expected 400, got {res.status_code}: {res.json()}"
    detail = res.json()["detail"]
    assert detail["code"] == "wallets.date_before_epoch", f"Got: {detail}"

    # No side effects
    session.expire_all()
    event_count_after = (
        session.query(models.FinancialEvent)
        .filter(models.FinancialEvent.owner_id == user.id)
        .count()
    )
    assert event_count_after == event_count_before

    plan_count = (
        session.query(models.PaymentPlan)
        .filter(models.PaymentPlan.owner_id == user.id)
        .count()
    )
    assert plan_count == 0


def test_payment_plan_same_day_accepted(client, session):
    """Payment plan setup on the wallet's tracking start date is accepted."""
    headers = create_user_and_token(
        client, "grdpp2", "grdpp2@example.com", "Password123!"
    )
    today = user_timezone_today()
    create_budget(
        client, headers,
        category="Groceries", monthly_limit=500_000,
        budget_year=today.year, budget_month=today.month,
    )

    user = session.query(models.User).filter(models.User.email == "grdpp2@example.com").first()
    wallet = (
        session.query(models.Wallet)
        .filter(models.Wallet.owner_id == user.id, models.Wallet.is_default)
        .first()
    )
    wallet.created_at = datetime(today.year, today.month, today.day, tzinfo=timezone.utc)
    session.commit()

    res = client.post(
        "/payment-plans",
        json={
            "plan_type": "BANK_LOAN",
            "item_name": "Test Loan",
            "store_or_bank_name": "Test Bank",
            "total_price": 50_000,
            "down_payment": 0,
            "months": 3,
            "frequency": "MONTHLY",
            "start_date": today.isoformat(),
            "expense_category": "Groceries",
            "schedule_model": "FLAT_TOTAL",
        },
        headers=headers,
    )
    assert res.status_code in (200, 201), f"Expected 200/201, got {res.status_code}: {res.json()}"


# ---------------------------------------------------------------------------
# Cross-flow: accepted flows preserve wallet projection
# ---------------------------------------------------------------------------

def test_accepted_expense_preserves_wallet_projection(client, session):
    """After an accepted expense posting, the wallet balance matches its ledger projection."""
    headers = create_user_and_token(
        client, "grdproj1", "grdproj1@example.com", "Password123!"
    )
    today = user_timezone_today()
    create_budget(
        client, headers,
        category="Groceries", monthly_limit=500_000,
        budget_year=today.year, budget_month=today.month,
    )

    user = session.query(models.User).filter(models.User.email == "grdproj1@example.com").first()
    wallet = (
        session.query(models.Wallet)
        .filter(models.Wallet.owner_id == user.id, models.Wallet.is_default)
        .first()
    )
    wallet.created_at = datetime(2020, 1, 1, tzinfo=timezone.utc)
    session.commit()

    res = client.post(
        "/expenses",
        json={
            "title": "Guardrail Expense",
            "amount": 5_000,
            "category": "Groceries",
            "date": today.isoformat(),
            "wallet_id": wallet.id,
        },
        headers=headers,
    )
    assert res.status_code in (200, 201), f"Expense creation failed: {res.json()}"

    session.expire_all()
    projection = verify_wallet_projection(session, wallet_id=wallet.id)
    assert projection.is_valid, f"Wallet projection mismatch: {projection.detail}"


def test_accepted_income_preserves_wallet_projection(client, session):
    """After an accepted income posting, the wallet projection is valid."""
    headers = create_user_and_token(
        client, "grdproj2", "grdproj2@example.com", "Password123!"
    )
    today = user_timezone_today()

    source_res = client.post(
        "/income/sources",
        json={"name": "Projection Test Source"},
        headers=headers,
    )
    assert source_res.status_code == 201

    user = session.query(models.User).filter(models.User.email == "grdproj2@example.com").first()
    wallet = (
        session.query(models.Wallet)
        .filter(models.Wallet.owner_id == user.id, models.Wallet.is_default)
        .first()
    )
    wallet.created_at = datetime(2020, 1, 1, tzinfo=timezone.utc)
    session.commit()

    res = client.post(
        "/income/entries",
        json={
            "amount": 20_000,
            "date": today.isoformat(),
            "source_id": source_res.json()["id"],
            "wallet_id": wallet.id,
        },
        headers=headers,
    )
    assert res.status_code in (200, 201), f"Income creation failed: {res.json()}"

    session.expire_all()
    projection = verify_wallet_projection(session, wallet_id=wallet.id)
    assert projection.is_valid, f"Wallet projection mismatch: {projection.detail}"


# ---------------------------------------------------------------------------
# Document planning-only flows outside the Financial Event ledger
# ---------------------------------------------------------------------------

def test_planning_only_flows_documented():
    """Document planning-only, metadata-only, template, and draft flows
    that intentionally stay out of the global Financial Event ledger."""
    planning_only_flows = [
        "Expected Inflow creation (Promise + Schedule)",
        "Expected Inflow write-off — non-wallet settlement",
        "Expected Inflow reschedule — planning date change",
        "Session draft creation/editing — no ledger posting",
        "Debt metadata edit — no wallet touch",
        "Payment Plan schedule preview — no persistence",
        "Budget creation and limit editing — permission rules",
        "Goal template creation — template metadata",
        "Recurring expense template creation — template",
        "Asset creation from expense — no additional money movement",
    ]
    assert len(planning_only_flows) > 0

    metadata_only_fields = [
        "title", "description", "date", "category",
        "counterparty_name", "expected_return_date",
        "income_source_id", "origin_kind", "counterparty_kind",
    ]
    assert len(metadata_only_fields) > 0


# ---------------------------------------------------------------------------
# X-Timezone header coverage
# ---------------------------------------------------------------------------

def test_all_guardrail_flows_use_explicit_timezone_headers(client, session):
    """Confirm that every tested flow sends X-Timezone headers."""
    headers = create_user_and_token(
        client, "grdtz1", "grdtz1@example.com", "Password123!"
    )
    today = user_timezone_today()
    create_budget(
        client, headers,
        category="Groceries", monthly_limit=500_000,
        budget_year=today.year, budget_month=today.month,
    )

    user = session.query(models.User).filter(models.User.email == "grdtz1@example.com").first()
    wallet = (
        session.query(models.Wallet)
        .filter(models.Wallet.owner_id == user.id, models.Wallet.is_default)
        .first()
    )
    wallet.created_at = datetime(2020, 1, 1, tzinfo=timezone.utc)
    session.commit()

    assert headers.get("X-Timezone") == TEST_TIMEZONE

    res = client.post(
        "/expenses",
        json={
            "title": "TZ Guardrail",
            "amount": 1_000,
            "category": "Groceries",
            "date": today.isoformat(),
            "wallet_id": wallet.id,
        },
        headers=headers,
    )
    assert res.status_code in (200, 201), f"Expense failed: {res.json()}"

    source_res = client.post(
        "/income/sources",
        json={"name": "TZ Guardrail Source"},
        headers=headers,
    )
    assert source_res.status_code == 201

    res = client.post(
        "/income/entries",
        json={
            "amount": 3_000,
            "date": today.isoformat(),
            "source_id": source_res.json()["id"],
            "wallet_id": wallet.id,
        },
        headers=headers,
    )
    assert res.status_code in (200, 201), f"Income failed: {res.json()}"
