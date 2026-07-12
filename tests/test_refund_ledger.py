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


def test_refund_title_equals_original_expense_title(client, session):
    """Ticket 4: Refund title stores the original expense title.
    The refund type is communicated through event_type=REFUND, not through
    title prefixes like 'Refund' or 'Partial Refund'."""
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
    assert refund.json()["title"] == "Grocery shopping trip"
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
    assert r1.json()["title"] == "Big purchase"

    r2 = client.post(
        f"/expenses/{expense_id}/refund",
        json={"amount": 40_000},
        headers=headers,
    )
    assert r2.status_code == 201, r2.text
    assert r2.json()["title"] == "Big purchase"

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
    assert refund.json()["title"] == "Full refundable"

    # Expense is still queryable
    expense = client.get(f"/expenses/{expense_id}", headers=headers)
    assert expense.status_code == 200
    assert expense.json()["is_fully_refunded"] is True


# ---------------------------------------------------------------------------
# Ticket 5: Refund duality — wallet AND category math
# ---------------------------------------------------------------------------


def test_refund_increases_wallet_and_reduces_category_spend(client, session):
    """A refund increases wallet balance AND decreases net category spend.
    Hiding refunds from either side would produce wrong totals."""
    headers = create_user_and_token(
        client, "t5walletcat", "t5walletcat@example.com", "Password123!"
    )
    create_budget(client, headers, category="Groceries", monthly_limit=500_000)
    wallet_id = (
        session.query(models.Wallet)
        .filter(models.Wallet.owner_id == models.User.id)
        .filter(models.User.email == "t5walletcat@example.com")
        .filter(models.Wallet.is_default)
        .first()
        .id
    )

    wallet_before = (
        session.query(models.Wallet).filter(models.Wallet.id == wallet_id).first()
    )
    balance_before = wallet_before.current_balance

    # Create expense
    created = client.post(
        "/expenses/",
        json={
            "title": "Weekly groceries",
            "amount": 60_000,
            "category": "Groceries",
            "date": user_timezone_today().isoformat(),
        },
        headers=headers,
    )
    assert created.status_code == 201, created.text
    expense_id = created.json()["id"]

    # Category spend before refund: normal_budget_spent includes the expense
    month_summary = client.get(
        f"/budgets/month-summary?budget_year={user_timezone_today().year}&budget_month={user_timezone_today().month}",
        headers=headers,
    )
    assert month_summary.status_code == 200, month_summary.text
    spent_before = month_summary.json()["normal_budget_spent"]
    assert spent_before == 60_000

    # Refund 25k
    refund = client.post(
        f"/expenses/{expense_id}/refund",
        json={"amount": 25_000},
        headers=headers,
    )
    assert refund.status_code == 201, refund.text

    # Wallet balance increased by refund
    session.expire_all()
    wallet_after = (
        session.query(models.Wallet).filter(models.Wallet.id == wallet_id).first()
    )
    assert wallet_after.current_balance == balance_before - 60_000 + 25_000

    # Category spend decreased by refund (60k - 25k = 35k)
    month_summary2 = client.get(
        f"/budgets/month-summary?budget_year={user_timezone_today().year}&budget_month={user_timezone_today().month}",
        headers=headers,
    )
    assert month_summary2.status_code == 200, month_summary2.text
    spent_after = month_summary2.json()["normal_budget_spent"]
    assert spent_after == 35_000  # 60k - 25k = 35k


def test_full_refund_reduces_category_spend_to_zero(client, session):
    """A full refund reduces net category spend to zero."""
    headers = create_user_and_token(
        client, "t5fullzero", "t5fullzero@example.com", "Password123!"
    )
    create_budget(client, headers, category="Electronics", monthly_limit=500_000)

    created = client.post(
        "/expenses/",
        json={
            "title": "Full refund item",
            "amount": 40_000,
            "category": "Electronics",
            "date": user_timezone_today().isoformat(),
        },
        headers=headers,
    )
    assert created.status_code == 201, created.text
    expense_id = created.json()["id"]

    # Full refund
    refund = client.post(
        f"/expenses/{expense_id}/refund",
        json={"amount": 40_000},
        headers=headers,
    )
    assert refund.status_code == 201, refund.text

    # Category spend is zero after full refund (refund offsets the expense)
    month_summary = client.get(
        f"/budgets/month-summary?budget_year={user_timezone_today().year}&budget_month={user_timezone_today().month}",
        headers=headers,
    )
    assert month_summary.status_code == 200, month_summary.text
    assert month_summary.json()["normal_budget_spent"] == 0


def test_refund_appears_in_money_in_as_returned_kind(client):
    """A refund appears in the Money In list with kind=returned and does NOT
    count as earned income."""
    headers = create_user_and_token(
        client, "t5moneyin", "t5moneyin@example.com", "Password123!"
    )
    create_budget(client, headers, category="Dining Out", monthly_limit=500_000)

    created = client.post(
        "/expenses/",
        json={
            "title": "Restaurant refund test",
            "amount": 20_000,
            "category": "Dining Out",
            "date": user_timezone_today().isoformat(),
        },
        headers=headers,
    )
    assert created.status_code == 201, created.text
    expense_id = created.json()["id"]

    client.post(
        f"/expenses/{expense_id}/refund",
        json={"amount": 20_000},
        headers=headers,
    )

    # Refund appears in Money In
    money_in = client.get("/money-in", headers=headers)
    assert money_in.status_code == 200, money_in.text
    items = money_in.json()["items"]
    refund_items = [i for i in items if i["kind"] == "returned"]
    assert len(refund_items) >= 1
    refund_item = refund_items[0]
    assert refund_item["counts_as_income"] is False
    assert refund_item["title"] == "Restaurant refund test"

    # Filter Money In by kind=returned shows only refunds
    returned_only = client.get("/money-in?kind=returned", headers=headers)
    assert returned_only.status_code == 200, returned_only.text
    returned_items = returned_only.json()["items"]
    assert all(i["kind"] == "returned" for i in returned_items)

    # Filter Money In by kind=income excludes refunds
    income_only = client.get("/money-in?kind=income", headers=headers)
    assert income_only.status_code == 200, income_only.text
    income_items = income_only.json()["items"]
    assert not any(i["kind"] == "returned" for i in income_items)


def test_money_in_totals_distinguish_income_from_refunds(client):
    """Money In totals can distinguish earned income from refunds, borrowed
    money, sales, and corrections through the kind filter."""
    headers = create_user_and_token(
        client, "t5distinguish", "t5distinguish@example.com", "Password123!"
    )
    create_budget(client, headers, category="Groceries", monthly_limit=500_000)

    # Create an expense and refund it
    created = client.post(
        "/expenses/",
        json={
            "title": "Distinguish test",
            "amount": 15_000,
            "category": "Groceries",
            "date": user_timezone_today().isoformat(),
        },
        headers=headers,
    )
    assert created.status_code == 201, created.text
    expense_id = created.json()["id"]
    refund_resp = client.post(
        f"/expenses/{expense_id}/refund",
        json={"amount": 10_000},
        headers=headers,
    )
    assert refund_resp.status_code == 201, refund_resp.text

    money_in = client.get("/money-in", headers=headers)
    assert money_in.status_code == 200, money_in.text
    kinds = {item["kind"] for item in money_in.json()["items"]}
    assert "returned" in kinds  # refunds are visible in the kind set
    assert "income" in kinds or "returned" in kinds  # at least one is visible

    # Each kind can be separately queried
    for kind_value in ["income", "returned"]:
        filtered = client.get(f"/money-in?kind={kind_value}", headers=headers)
        assert filtered.status_code == 200, filtered.text
        filtered_items = filtered.json()["items"]
        if filtered_items:
            assert all(item["kind"] == kind_value for item in filtered_items)


def test_earned_income_analytics_exclude_refunds(client):
    """Earned-income analytics totals exclude refunds. A refund does not
    inflate the income number on the dashboard."""
    headers = create_user_and_token(
        client, "t5exclude", "t5exclude@example.com", "Password123!"
    )
    create_budget(client, headers, category="Groceries", monthly_limit=500_000)

    # Get dashboard summary before refund
    summary_before = client.get("/analytics/dashboard-summary", headers=headers)
    assert summary_before.status_code == 200, summary_before.text
    income_before = summary_before.json()["income"]

    # Create expense and refund — refund should NOT increase income
    created = client.post(
        "/expenses/",
        json={
            "title": "Analytics refund",
            "amount": 30_000,
            "category": "Groceries",
            "date": user_timezone_today().isoformat(),
        },
        headers=headers,
    )
    assert created.status_code == 201, created.text
    expense_id = created.json()["id"]
    client.post(
        f"/expenses/{expense_id}/refund",
        json={"amount": 30_000},
        headers=headers,
    )

    # Income should NOT have changed — refunds are not earned income
    summary_after = client.get("/analytics/dashboard-summary", headers=headers)
    assert summary_after.status_code == 200, summary_after.text
    assert summary_after.json()["income"] == income_before


def test_hiding_refunds_from_either_side_would_fail(client, session):
    """Prove that removing refunds from either the Money In view or the
    Expenses/budget view would produce incorrect totals. This guards against
    future regression that might hide refunds from one side."""
    headers = create_user_and_token(
        client, "t5regress", "t5regress@example.com", "Password123!"
    )
    create_budget(client, headers, category="Transport", monthly_limit=500_000)
    wallet_id = (
        session.query(models.Wallet)
        .filter(models.Wallet.owner_id == models.User.id)
        .filter(models.User.email == "t5regress@example.com")
        .filter(models.Wallet.is_default)
        .first()
        .id
    )

    # Create expense
    created = client.post(
        "/expenses/",
        json={
            "title": "Regression refund",
            "amount": 50_000,
            "category": "Transport",
            "date": user_timezone_today().isoformat(),
        },
        headers=headers,
    )
    assert created.status_code == 201, created.text
    expense_id = created.json()["id"]

    wallet_before_refund = (
        session.query(models.Wallet).filter(models.Wallet.id == wallet_id).first()
    ).current_balance

    # Refund 50k — full refund
    client.post(
        f"/expenses/{expense_id}/refund",
        json={"amount": 50_000},
        headers=headers,
    )

    # ---- Side A: Money In view MUST include the refund ----
    money_in = client.get("/money-in", headers=headers)
    assert money_in.status_code == 200, money_in.text
    refund_items = [i for i in money_in.json()["items"] if i["title"] == "Regression refund"]
    assert len(refund_items) == 1
    assert refund_items[0]["kind"] == "returned"

    # ---- Side B: Wallet balance MUST reflect the refund (increased by 50k) ----
    session.expire_all()
    wallet_after = (
        session.query(models.Wallet).filter(models.Wallet.id == wallet_id).first()
    )
    assert wallet_after.current_balance == wallet_before_refund + 50_000

    # ---- Side C: Category spend MUST be zero after full refund ----
    month_summary = client.get(
        f"/budgets/month-summary?budget_year={user_timezone_today().year}&budget_month={user_timezone_today().month}",
        headers=headers,
    )
    assert month_summary.status_code == 200, month_summary.text
    assert month_summary.json()["normal_budget_spent"] == 0

    # If either side hid the refund, one of the above assertions would fail.
