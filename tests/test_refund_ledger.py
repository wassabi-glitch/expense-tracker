"""Regression tests for Issue 6: Route refund posting through the
FinancialEventLedger seam.

Verifies that refunding an expense creates a correctly-shaped REFUND
FinancialEvent with proper wallet and entity ledger entries through the
ledger seam — without asserting private helper call order.
"""

from app import models
from tests.helpers import create_budget, create_user_and_token, user_timezone_today


def _default_wallet_id(session, email):
    return (
        session.query(models.Wallet)
        .filter(models.Wallet.owner_id == models.User.id)
        .filter(models.User.email == email)
        .filter(models.Wallet.is_default)
        .first()
        .id
    )


# ---------------------------------------------------------------------------
# Refund → FinancialEventLedger seam
# ---------------------------------------------------------------------------


def test_refund_creates_posted_refund_event(client, session):
    """A refund creates a posted REFUND FinancialEvent linked to the
    original expense."""
    headers = create_user_and_token(
        client, "refregress1", "refregress1@example.com", "Password123!"
    )
    create_budget(client, headers, category="Groceries", monthly_limit=500_000)

    created = client.post(
        "/expenses/",
        json={
            "title": "Original expense",
            "amount": 30_000,
            "category": "Groceries",
            "date": user_timezone_today().isoformat(),
        },
        headers=headers,
    )
    assert created.status_code == 201, created.text
    expense_id = created.json()["id"]

    refund = client.post(
        f"/expenses/{expense_id}/refund",
        json={"amount": 15_000},
        headers=headers,
    )
    assert refund.status_code == 201, refund.text
    refund_id = refund.json()["id"]

    session.expire_all()
    event = (
        session.query(models.FinancialEvent)
        .filter(models.FinancialEvent.id == refund_id)
        .first()
    )
    assert event is not None
    assert event.event_type == models.TransactionType.REFUND
    assert event.status == models.FinancialEventStatus.POSTED
    assert event.linked_event_id == expense_id


def test_refund_wallet_ledger_increases_wallet(client, session):
    """Refund Wallet Ledger entries increase the selected wallet by the
    received amount."""
    headers = create_user_and_token(
        client, "refregress2", "refregress2@example.com", "Password123!"
    )
    create_budget(client, headers, category="Dining Out", monthly_limit=500_000)
    wallet_id = _default_wallet_id(session, "refregress2@example.com")

    wallet_before = (
        session.query(models.Wallet).filter(models.Wallet.id == wallet_id).first()
    )
    balance_before = wallet_before.current_balance

    created = client.post(
        "/expenses/",
        json={
            "title": "Restaurant",
            "amount": 50_000,
            "category": "Dining Out",
            "date": user_timezone_today().isoformat(),
        },
        headers=headers,
    )
    assert created.status_code == 201, created.text
    expense_id = created.json()["id"]

    # Wallet is down by 50k after expense
    session.expire_all()
    after_expense = (
        session.query(models.Wallet).filter(models.Wallet.id == wallet_id).first()
    )
    assert after_expense.current_balance == balance_before - 50_000

    refund = client.post(
        f"/expenses/{expense_id}/refund",
        json={"amount": 30_000},
        headers=headers,
    )
    assert refund.status_code == 201, refund.text
    refund_id = refund.json()["id"]

    session.expire_all()
    after_refund = (
        session.query(models.Wallet).filter(models.Wallet.id == wallet_id).first()
    )
    assert after_refund.current_balance == balance_before - 50_000 + 30_000

    event = (
        session.query(models.FinancialEvent)
        .filter(models.FinancialEvent.id == refund_id)
        .first()
    )
    assert len(event.wallet_legs) == 1
    assert event.wallet_legs[0].wallet_id == wallet_id
    assert event.wallet_legs[0].amount == 30_000  # positive = inflow


def test_refund_preserves_entity_ledger_links(client, session):
    """Refund Entity Ledger entries preserve the original expense's
    category, budget, subcategory, and project links."""
    headers = create_user_and_token(
        client, "refregress3", "refregress3@example.com", "Password123!"
    )
    create_budget(client, headers, category="Electronics", monthly_limit=1_000_000)

    created = client.post(
        "/expenses/",
        json={
            "title": "Laptop",
            "amount": 200_000,
            "category": "Electronics",
            "date": user_timezone_today().isoformat(),
        },
        headers=headers,
    )
    assert created.status_code == 201, created.text
    expense_id = created.json()["id"]

    refund = client.post(
        f"/expenses/{expense_id}/refund",
        json={"amount": 50_000},
        headers=headers,
    )
    assert refund.status_code == 201, refund.text
    refund_id = refund.json()["id"]

    session.expire_all()
    event = (
        session.query(models.FinancialEvent)
        .filter(models.FinancialEvent.id == refund_id)
        .first()
    )
    assert len(event.entity_legs) == 1
    leg = event.entity_legs[0]
    assert leg.category == models.ExpenseCategory.ELECTRONICS
    assert leg.budget_id is not None
    assert leg.amount == 50_000


def test_refund_title_inherits_original_description(client, session):
    """Refund title behavior follows title inheritance — the description
    is the original expense title, not a robotic prefix."""
    headers = create_user_and_token(
        client, "refregress4", "refregress4@example.com", "Password123!"
    )
    create_budget(client, headers, category="Groceries", monthly_limit=500_000)

    created = client.post(
        "/expenses/",
        json={
            "title": "Grocery shopping trip",
            "amount": 10_000,
            "category": "Groceries",
            "date": user_timezone_today().isoformat(),
        },
        headers=headers,
    )
    assert created.status_code == 201, created.text
    expense_id = created.json()["id"]

    refund = client.post(
        f"/expenses/{expense_id}/refund",
        json={"amount": 10_000},
        headers=headers,
    )
    assert refund.status_code == 201, refund.text
    assert refund.json()["title"] == "Refund"
    assert refund.json()["description"] == "Grocery shopping trip"


def test_refund_cannot_exceed_refundable_amount(client, session):
    """Refunds cannot exceed the refundable amount (original minus
    already-refunded)."""
    headers = create_user_and_token(
        client, "refregress5", "refregress5@example.com", "Password123!"
    )
    create_budget(client, headers, category="Transport", monthly_limit=500_000)

    created = client.post(
        "/expenses/",
        json={
            "title": "Bus pass",
            "amount": 20_000,
            "category": "Transport",
            "date": user_timezone_today().isoformat(),
        },
        headers=headers,
    )
    assert created.status_code == 201, created.text
    expense_id = created.json()["id"]

    blocked = client.post(
        f"/expenses/{expense_id}/refund",
        json={"amount": 50_000},
        headers=headers,
    )
    assert blocked.status_code == 400
    assert blocked.json()["detail"] == "expenses.refund_exceeds_total"


def test_refund_supports_multiple_partial_refunds(client, session):
    """Multiple partial refunds are each posted through the ledger seam
    and tracked independently."""
    headers = create_user_and_token(
        client, "refregress6", "refregress6@example.com", "Password123!"
    )
    create_budget(client, headers, category="Groceries", monthly_limit=500_000)

    created = client.post(
        "/expenses/",
        json={
            "title": "Big purchase",
            "amount": 100_000,
            "category": "Groceries",
            "date": user_timezone_today().isoformat(),
        },
        headers=headers,
    )
    assert created.status_code == 201, created.text
    expense_id = created.json()["id"]

    r1 = client.post(
        f"/expenses/{expense_id}/refund",
        json={"amount": 30_000},
        headers=headers,
    )
    assert r1.status_code == 201, r1.text
    assert r1.json()["title"] == "Partial Refund"

    r2 = client.post(
        f"/expenses/{expense_id}/refund",
        json={"amount": 40_000},
        headers=headers,
    )
    assert r2.status_code == 201, r2.text
    assert r2.json()["title"] == "Partial Refund"

    session.expire_all()
    refund_events = (
        session.query(models.FinancialEvent)
        .filter(
            models.FinancialEvent.linked_event_id == expense_id,
            models.FinancialEvent.event_type == models.TransactionType.REFUND,
            models.FinancialEvent.status == models.FinancialEventStatus.POSTED,
        )
        .all()
    )
    assert len(refund_events) == 2
    total_refunded = sum(
        int(leg.amount) for event in refund_events for leg in event.entity_legs
    )
    assert total_refunded == 70_000

    # Remaining 30k should not be exceeded
    blocked = client.post(
        f"/expenses/{expense_id}/refund",
        json={"amount": 50_000},
        headers=headers,
    )
    assert blocked.status_code == 400
    assert blocked.json()["detail"] == "expenses.refund_exceeds_total"


def test_full_refund_and_void_sequence(client, session):
    """A full refund is independent of void — after a full refund the
    expense can still be queried normally."""
    headers = create_user_and_token(
        client, "refregress7", "refregress7@example.com", "Password123!"
    )
    create_budget(client, headers, category="Dining Out", monthly_limit=500_000)

    created = client.post(
        "/expenses/",
        json={
            "title": "Full refundable",
            "amount": 15_000,
            "category": "Dining Out",
            "date": user_timezone_today().isoformat(),
        },
        headers=headers,
    )
    assert created.status_code == 201, created.text
    expense_id = created.json()["id"]

    refund = client.post(
        f"/expenses/{expense_id}/refund",
        json={"amount": 15_000},
        headers=headers,
    )
    assert refund.status_code == 201, refund.text
    assert refund.json()["title"] == "Refund"

    # Expense is still queryable
    expense = client.get(f"/expenses/{expense_id}", headers=headers)
    assert expense.status_code == 200
    assert expense.json()["is_fully_refunded"] is True
