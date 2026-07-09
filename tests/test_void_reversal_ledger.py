"""Regression tests for Issue 5: Move expense void and reversal mechanics
behind the FinancialEventLedger seam.

Verifies that voiding a posted expense creates a correctly-shaped reversal
through the ledger seam without asserting private helper call order.
"""

from app import models
from tests.helpers import create_budget, create_user_and_token, user_timezone_today


# ---------------------------------------------------------------------------
# Expense void / reversal → FinancialEventLedger seam
# ---------------------------------------------------------------------------


def test_void_marks_original_event_voided(client, session):
    """Voiding a posted expense marks the original event VOIDED with a
    linked reversal event ID."""
    headers = create_user_and_token(
        client, "voidregress1", "voidregress1@example.com", "Password123!"
    )
    create_budget(client, headers, category="Groceries", monthly_limit=500_000)

    created = client.post(
        "/expenses/",
        json={
            "title": "To void",
            "amount": 30_000,
            "category": "Groceries",
            "date": user_timezone_today().isoformat(),
        },
        headers=headers,
    )
    assert created.status_code == 201, created.text
    expense_id = created.json()["id"]

    deleted = client.delete(f"/expenses/{expense_id}", headers=headers)
    assert deleted.status_code == 204

    session.expire_all()
    original = (
        session.query(models.FinancialEvent)
        .filter(models.FinancialEvent.id == expense_id)
        .first()
    )
    assert original is not None
    assert original.status == models.FinancialEventStatus.VOIDED
    assert original.void_reversal_event_id is not None


def test_void_creates_reversal_financial_event(client, session):
    """Voiding creates exactly one reversal FinancialEvent with
    REVERSAL status and VOID_REVERSAL reference type."""
    headers = create_user_and_token(
        client, "voidregress2", "voidregress2@example.com", "Password123!"
    )
    create_budget(client, headers, category="Transport", monthly_limit=500_000)

    created = client.post(
        "/expenses/",
        json={
            "title": "Expense to reverse",
            "amount": 25_000,
            "category": "Transport",
            "date": user_timezone_today().isoformat(),
        },
        headers=headers,
    )
    assert created.status_code == 201, created.text
    expense_id = created.json()["id"]

    client.delete(f"/expenses/{expense_id}", headers=headers)

    session.expire_all()
    original = (
        session.query(models.FinancialEvent)
        .filter(models.FinancialEvent.id == expense_id)
        .first()
    )
    reversal = (
        session.query(models.FinancialEvent)
        .filter(models.FinancialEvent.id == original.void_reversal_event_id)
        .first()
    )
    assert reversal is not None
    assert reversal.status == models.FinancialEventStatus.REVERSAL
    assert reversal.reference_type == models.ReferenceType.VOID_REVERSAL
    assert reversal.reverses_event_id == original.id


def test_void_counter_balances_wallet_ledger(client, session):
    """Reversal Wallet Ledger entries counter-balance the original
    entries with opposite signs."""
    headers = create_user_and_token(
        client, "voidregress3", "voidregress3@example.com", "Password123!"
    )
    create_budget(client, headers, category="Dining Out", monthly_limit=500_000)

    created = client.post(
        "/expenses/",
        json={
            "title": "Dinner",
            "amount": 40_000,
            "category": "Dining Out",
            "date": user_timezone_today().isoformat(),
        },
        headers=headers,
    )
    assert created.status_code == 201, created.text
    expense_id = created.json()["id"]

    client.delete(f"/expenses/{expense_id}", headers=headers)

    session.expire_all()
    original = (
        session.query(models.FinancialEvent)
        .filter(models.FinancialEvent.id == expense_id)
        .first()
    )
    reversal = (
        session.query(models.FinancialEvent)
        .filter(models.FinancialEvent.id == original.void_reversal_event_id)
        .first()
    )

    assert len(reversal.wallet_legs) == len(original.wallet_legs)
    for orig_leg in original.wallet_legs:
        rev_leg = next(
            (leg for leg in reversal.wallet_legs if leg.wallet_id == orig_leg.wallet_id),
            None,
        )
        assert rev_leg is not None, f"No reversal leg for wallet {orig_leg.wallet_id}"
        assert rev_leg.amount == -orig_leg.amount


def test_void_counter_balances_entity_ledger(client, session):
    """Reversal Entity Ledger entries counter-balance the original
    entries with opposite signs and preserve link metadata."""
    headers = create_user_and_token(
        client, "voidregress4", "voidregress4@example.com", "Password123!"
    )
    create_budget(client, headers, category="Electronics", monthly_limit=1_000_000)

    created = client.post(
        "/expenses/",
        json={
            "title": "Gadget",
            "amount": 100_000,
            "category": "Electronics",
            "date": user_timezone_today().isoformat(),
        },
        headers=headers,
    )
    assert created.status_code == 201, created.text
    expense_id = created.json()["id"]

    client.delete(f"/expenses/{expense_id}", headers=headers)

    session.expire_all()
    original = (
        session.query(models.FinancialEvent)
        .filter(models.FinancialEvent.id == expense_id)
        .first()
    )
    reversal = (
        session.query(models.FinancialEvent)
        .filter(models.FinancialEvent.id == original.void_reversal_event_id)
        .first()
    )

    assert len(reversal.entity_legs) == len(original.entity_legs)
    orig_leg = original.entity_legs[0]
    rev_leg = reversal.entity_legs[0]
    assert rev_leg.amount == -orig_leg.amount
    assert rev_leg.category == orig_leg.category
    assert rev_leg.budget_id == orig_leg.budget_id


def test_void_restores_wallet_balance(client, session):
    """Wallet balances are restored by the reversal exactly once."""
    headers = create_user_and_token(
        client, "voidregress5", "voidregress5@example.com", "Password123!"
    )
    create_budget(client, headers, category="Groceries", monthly_limit=500_000)

    wallet_before = (
        session.query(models.Wallet)
        .filter(models.Wallet.owner_id == models.User.id)
        .filter(models.User.email == "voidregress5@example.com")
        .filter(models.Wallet.is_default)
        .first()
    )
    balance_before = wallet_before.current_balance

    created = client.post(
        "/expenses/",
        json={
            "title": "Restore test",
            "amount": 50_000,
            "category": "Groceries",
            "date": user_timezone_today().isoformat(),
        },
        headers=headers,
    )
    assert created.status_code == 201, created.text
    expense_id = created.json()["id"]

    session.expire_all()
    after_expense = (
        session.query(models.Wallet)
        .filter(models.Wallet.id == wallet_before.id)
        .first()
    )
    assert after_expense.current_balance == balance_before - 50_000

    client.delete(f"/expenses/{expense_id}", headers=headers)

    session.expire_all()
    after_void = (
        session.query(models.Wallet)
        .filter(models.Wallet.id == wallet_before.id)
        .first()
    )
    assert after_void.current_balance == balance_before


def test_void_rejected_for_session_expense(client, session):
    """Session expenses cannot be voided through this path."""
    headers = create_user_and_token(
        client, "voidregress6", "voidregress6@example.com", "Password123!"
    )
    create_budget(client, headers, category="Groceries", monthly_limit=1_000_000)

    # Create and finalize a session
    wallet_id = (
        session.query(models.Wallet)
        .filter(models.Wallet.owner_id == models.User.id)
        .filter(models.User.email == "voidregress6@example.com")
        .filter(models.Wallet.is_default)
        .first()
        .id
    )
    draft = client.post(
        "/expenses/session-drafts",
        json={
            "title": "Session",
            "date": user_timezone_today().isoformat(),
            "amount_paid": 10_000,
        },
        headers=headers,
    )
    assert draft.status_code == 201, draft.text
    draft_id = draft.json()["id"]
    client.post(
        f"/expenses/session-drafts/{draft_id}/items",
        json={"label": "Item", "original_amount": 10_000, "category": "Groceries"},
        headers=headers,
    )
    client.post(
        f"/expenses/session-drafts/{draft_id}/wallet-allocations",
        json={"wallet_id": wallet_id, "amount": 10_000},
        headers=headers,
    )
    finalized = client.post(f"/expenses/session-drafts/{draft_id}/finalize", headers=headers)
    assert finalized.status_code == 201, finalized.text
    session_event_id = finalized.json()["id"]

    blocked = client.delete(f"/expenses/{session_event_id}", headers=headers)
    assert blocked.status_code == 400
    assert blocked.json()["detail"] == "expenses.session_void_not_supported"


def test_void_rejected_when_refund_exists(client, session):
    """An expense with a posted refund cannot be voided."""
    headers = create_user_and_token(
        client, "voidregress7", "voidregress7@example.com", "Password123!"
    )
    create_budget(client, headers, category="Groceries", monthly_limit=500_000)

    created = client.post(
        "/expenses/",
        json={
            "title": "Refund lock test",
            "amount": 20_000,
            "category": "Groceries",
            "date": user_timezone_today().isoformat(),
        },
        headers=headers,
    )
    assert created.status_code == 201, created.text
    expense_id = created.json()["id"]

    client.post(
        f"/expenses/{expense_id}/refund",
        json={"amount": 5_000},
        headers=headers,
    )

    blocked = client.delete(f"/expenses/{expense_id}", headers=headers)
    assert blocked.status_code == 400
    assert blocked.json()["detail"] == "expenses.has_refund_lock"
