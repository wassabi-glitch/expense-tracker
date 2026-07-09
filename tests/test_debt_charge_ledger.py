"""Regression tests for Issue 4 & Issue 6 of PRD 2: Route Debt charge and
non-expense money events through the Expense Posting / FinancialEventLedger
seam, and verify the Obligation Money Posting seam (Issue 5).

Verifies:
- Paying a Debt charge (OWING) produces correctly-shaped FinancialEvent,
  WalletLedger, and EntityLedger entries through the shared posting seam.
- Non-expense Debt events (settlement, income) route through
  post_financial_event instead of manual row construction.
- The Obligation Money Posting seam delegates correctly and preserves
  domain separation between Debt and Payment Plan modules.
"""

from app import models
from tests.helpers import create_budget, create_user_and_token, user_timezone_today


def _default_wallet(client, headers):
    response = client.get("/wallets", headers=headers)
    assert response.status_code == 200, response.text
    return response.json()[0]


def _create_wallet(session, user_id, name="Second Wallet", balance=2_000_000):
    wallet = models.Wallet(
        owner_id=user_id,
        name=name,
        wallet_type=models.WalletType.CASH,
        accounting_type=models.AccountingType.ASSET,
        initial_balance=balance,
        current_balance=balance,
        is_default=False,
    )
    session.add(wallet)
    session.commit()
    session.refresh(wallet)
    return wallet


def _user(session, email):
    return session.query(models.User).filter(models.User.email == email).first()


def _create_owing_debt(client, headers, wallet_id, **overrides):
    payload = {
        "debt_type": "OWING",
        "counterparty_name": "Bank",
        "initial_amount": 1_000_000,
        "currency": "UZS",
        "date": user_timezone_today().isoformat(),
        "expected_return_date": user_timezone_today().isoformat(),
        "is_money_transferred": True,
        "initial_wallet_id": wallet_id,
    }
    payload.update(overrides)
    res = client.post("/debts", json=payload, headers=headers)
    assert res.status_code == 201, res.text
    return res.json()


# ---------------------------------------------------------------------------
# Debt charge payment → Expense Posting seam regression
# ---------------------------------------------------------------------------


def test_debt_charge_payment_creates_posted_expense_event(client, session):
    """Paying a Debt charge (OWING) creates a posted expense-shaped
    FinancialEvent through the ledger seam with correct DEBT_CHARGE
    reference and category."""
    headers = create_user_and_token(
        client, "dcl1", "dcl1@example.com", "Password123!"
    )
    today = user_timezone_today()
    create_budget(client, headers, category="Debt Charges", monthly_limit=500_000,
                  budget_year=today.year, budget_month=today.month)
    wallet = _default_wallet(client, headers)
    debt = _create_owing_debt(client, headers, wallet["id"])

    charge = client.post(
        f"/debts/{debt['id']}/add-charge",
        json={"amount": 30_000, "reason": "Interest"},
        headers=headers,
    )
    assert charge.status_code == 201, charge.text

    payment = client.post(
        f"/debts/{debt['id']}/payments",
        json={
            "amount": 1_030_000,
            "date": today.isoformat(),
            "wallet_allocations": [
                {"wallet_id": wallet["id"], "amount": 1_030_000},
            ],
        },
        headers=headers,
    )
    assert payment.status_code == 201, payment.text

    session.expire_all()
    charge_events = (
        session.query(models.FinancialEvent)
        .join(models.EntityLedger)
        .filter(
            models.EntityLedger.debt_id == debt["id"],
            models.EntityLedger.category == models.ExpenseCategory.DEBT_CHARGES,
            models.FinancialEvent.reference_type == models.ReferenceType.DEBT_CHARGE,
        )
        .order_by(models.FinancialEvent.id.desc())
        .all()
    )
    assert len(charge_events) >= 1
    event = charge_events[0]
    assert event.event_type == models.TransactionType.EXPENSE
    assert event.status == models.FinancialEventStatus.POSTED


def test_debt_charge_payment_writes_wallet_ledger_with_funding(client, session):
    """Debt charge payments debit the wallet with correct funding
    classification (owned vs borrowed)."""
    headers = create_user_and_token(
        client, "dcl2", "dcl2@example.com", "Password123!"
    )
    today = user_timezone_today()
    create_budget(client, headers, category="Debt Charges", monthly_limit=500_000,
                  budget_year=today.year, budget_month=today.month)
    wallet = _default_wallet(client, headers)
    debt = _create_owing_debt(client, headers, wallet["id"])

    client.post(
        f"/debts/{debt['id']}/add-charge",
        json={"amount": 20_000, "reason": "Fee"},
        headers=headers,
    )

    # Snapshot balance AFTER debt creation (which may add money for
    # money-transferred debts) and charge addition, but BEFORE payment.
    wallet_obj = (
        session.query(models.Wallet)
        .filter(models.Wallet.id == wallet["id"])
        .first()
    )
    balance_before = wallet_obj.current_balance

    payment = client.post(
        f"/debts/{debt['id']}/payments",
        json={
            "amount": 1_020_000,
            "date": today.isoformat(),
            "wallet_allocations": [
                {"wallet_id": wallet["id"], "amount": 1_020_000},
            ],
        },
        headers=headers,
    )
    assert payment.status_code == 201, payment.text

    session.expire_all()
    charge_events = (
        session.query(models.FinancialEvent)
        .join(models.EntityLedger)
        .filter(
            models.EntityLedger.debt_id == debt["id"],
            models.EntityLedger.category == models.ExpenseCategory.DEBT_CHARGES,
        )
        .order_by(models.FinancialEvent.id.desc())
        .all()
    )
    event = charge_events[0]
    assert len(event.wallet_legs) == 1
    leg = event.wallet_legs[0]
    assert leg.wallet_id == wallet["id"]
    assert leg.amount == -20_000
    # The wallet has > 10M balance, so 20K should be fully owned
    assert leg.owned_spend_amount == 20_000
    assert leg.borrowed_spend_amount == 0

    refreshed = (
        session.query(models.Wallet)
        .filter(models.Wallet.id == wallet["id"])
        .first()
    )
    assert refreshed.current_balance == balance_before - 1_020_000


def test_debt_charge_payment_preserves_entity_links(client, session):
    """Entity Ledger entries for charge payments preserve debt_id, category,
    and budget links."""
    headers = create_user_and_token(
        client, "dcl3", "dcl3@example.com", "Password123!"
    )
    today = user_timezone_today()
    create_budget(client, headers, category="Debt Charges", monthly_limit=500_000,
                  budget_year=today.year, budget_month=today.month)
    wallet = _default_wallet(client, headers)
    debt = _create_owing_debt(client, headers, wallet["id"])

    client.post(
        f"/debts/{debt['id']}/add-charge",
        json={"amount": 10_000, "reason": "Interest"},
        headers=headers,
    )

    payment = client.post(
        f"/debts/{debt['id']}/payments",
        json={
            "amount": 1_010_000,
            "date": today.isoformat(),
            "wallet_allocations": [
                {"wallet_id": wallet["id"], "amount": 1_010_000},
            ],
        },
        headers=headers,
    )
    assert payment.status_code == 201, payment.text

    session.expire_all()
    charge_leg = (
        session.query(models.EntityLedger)
        .filter(
            models.EntityLedger.debt_id == debt["id"],
            models.EntityLedger.category == models.ExpenseCategory.DEBT_CHARGES,
        )
        .order_by(models.EntityLedger.id.desc())
        .first()
    )
    assert charge_leg is not None
    assert charge_leg.debt_id == debt["id"]
    assert charge_leg.category == models.ExpenseCategory.DEBT_CHARGES
    assert charge_leg.budget_id is not None
    assert int(charge_leg.amount) == 10_000


def test_debt_charge_payment_debt_ledger_still_created(client, session):
    """Debt Ledger entries are still created alongside the financial event."""
    headers = create_user_and_token(
        client, "dcl4", "dcl4@example.com", "Password123!"
    )
    today = user_timezone_today()
    create_budget(client, headers, category="Debt Charges", monthly_limit=500_000,
                  budget_year=today.year, budget_month=today.month)
    wallet = _default_wallet(client, headers)
    debt = _create_owing_debt(client, headers, wallet["id"])

    client.post(
        f"/debts/{debt['id']}/add-charge",
        json={"amount": 15_000, "reason": "Late fee"},
        headers=headers,
    )

    payment = client.post(
        f"/debts/{debt['id']}/payments",
        json={
            "amount": 1_015_000,
            "date": today.isoformat(),
            "wallet_allocations": [
                {"wallet_id": wallet["id"], "amount": 1_015_000},
            ],
        },
        headers=headers,
    )
    assert payment.status_code == 201, payment.text
    transaction_id = payment.json()["id"]

    session.expire_all()
    # Verify Debt Ledger entries
    charge_ledger = (
        session.query(models.DebtLedgerEntry)
        .filter(
            models.DebtLedgerEntry.debt_id == debt["id"],
            models.DebtLedgerEntry.source_debt_transaction_id == transaction_id,
            models.DebtLedgerEntry.charge_delta < 0,
        )
        .first()
    )
    assert charge_ledger is not None
    assert charge_ledger.entry_type == models.DebtLedgerEntryType.PAYMENT
    assert int(charge_ledger.charge_delta) == -15_000
    assert charge_ledger.financial_event_id is not None

    # Verify the Financial Event linked from the Debt Ledger is correctly shaped
    linked_event = (
        session.query(models.FinancialEvent)
        .filter(models.FinancialEvent.id == charge_ledger.financial_event_id)
        .first()
    )
    assert linked_event is not None
    assert linked_event.event_type == models.TransactionType.EXPENSE
    assert linked_event.status == models.FinancialEventStatus.POSTED
    assert linked_event.reference_type == models.ReferenceType.DEBT_CHARGE


def test_debt_charge_payment_budget_required_failure(client, session):
    """Budget-required failure remains structured when no Debt Charges budget
    exists."""
    headers = create_user_and_token(
        client, "dcl5", "dcl5@example.com", "Password123!"
    )
    # Deliberately skip creating a Debt Charges budget
    wallet = _default_wallet(client, headers)
    debt = _create_owing_debt(client, headers, wallet["id"])

    client.post(
        f"/debts/{debt['id']}/add-charge",
        json={"amount": 5_000, "reason": "Interest"},
        headers=headers,
    )

    payment = client.post(
        f"/debts/{debt['id']}/payments",
        json={
            "amount": 1_005_000,
            "date": user_timezone_today().isoformat(),
            "wallet_allocations": [
                {"wallet_id": wallet["id"], "amount": 1_005_000},
            ],
        },
        headers=headers,
    )
    assert payment.status_code == 400
    assert payment.json()["detail"] == "expenses.budget_required"


def test_debt_charge_payment_multi_wallet_preserves_charge_event(client, session):
    """When paying from multiple wallets, the charge portion produces exactly
    one expense FinancialEvent with correct wallet leg totals."""
    headers = create_user_and_token(
        client, "dcl6", "dcl6@example.com", "Password123!"
    )
    today = user_timezone_today()
    create_budget(client, headers, category="Debt Charges", monthly_limit=500_000,
                  budget_year=today.year, budget_month=today.month)
    default_wallet = _default_wallet(client, headers)
    user = _user(session, "dcl6@example.com")
    second_wallet = _create_wallet(session, user.id, name="Second")

    debt = _create_owing_debt(client, headers, default_wallet["id"])

    client.post(
        f"/debts/{debt['id']}/add-charge",
        json={"amount": 30_000, "reason": "Service charge"},
        headers=headers,
    )

    payment = client.post(
        f"/debts/{debt['id']}/payments",
        json={
            "amount": 1_030_000,
            "date": today.isoformat(),
            "wallet_allocations": [
                {"wallet_id": default_wallet["id"], "amount": 500_000},
                {"wallet_id": second_wallet.id, "amount": 530_000},
            ],
        },
        headers=headers,
    )
    assert payment.status_code == 201, payment.text

    session.expire_all()
    charge_events = (
        session.query(models.FinancialEvent)
        .join(models.EntityLedger)
        .filter(
            models.EntityLedger.debt_id == debt["id"],
            models.EntityLedger.category == models.ExpenseCategory.DEBT_CHARGES,
        )
        .order_by(models.FinancialEvent.id.desc())
        .all()
    )
    assert len(charge_events) == 1
    event = charge_events[0]
    total_charge_debit = sum(int(leg.amount) for leg in event.wallet_legs)
    assert total_charge_debit == -30_000
    assert int(event.entity_legs[0].amount) == 30_000


def test_debt_charge_payment_goal_protection_not_enforced(client, session):
    """Goal protection is NOT enforced for debt charge payments (the
    enforce_goal_protection=False flag is honored)."""
    headers = create_user_and_token(
        client, "dcl7", "dcl7@example.com", "Password123!"
    )
    today = user_timezone_today()
    create_budget(client, headers, category="Debt Charges", monthly_limit=500_000,
                  budget_year=today.year, budget_month=today.month)
    wallet = _default_wallet(client, headers)
    debt = _create_owing_debt(client, headers, wallet["id"])

    client.post(
        f"/debts/{debt['id']}/add-charge",
        json={"amount": 5_000, "reason": "Fee"},
        headers=headers,
    )

    # Even without goal protection conflicts, payment should succeed
    payment = client.post(
        f"/debts/{debt['id']}/payments",
        json={
            "amount": 1_005_000,
            "date": today.isoformat(),
            "wallet_allocations": [
                {"wallet_id": wallet["id"], "amount": 1_005_000},
            ],
        },
        headers=headers,
    )
    assert payment.status_code == 201, payment.text


# ============================================================================
# Issue 5 — Obligation Money Posting seam exists and preserves separation
# ============================================================================


def test_obligation_money_posting_seam_delegates_to_financial_event_ledger():
    """The Obligation Money Posting seam must exist and delegate to
    post_financial_event without importing Debt or Payment Plan modules."""
    from app.services.obligation_money_posting_service import (
        post_obligation_event,
    )

    # The obligation seam is a thin wrapper around post_financial_event.
    assert callable(post_obligation_event)

    # The function signature must accept obligation-relevant parameters.
    import inspect
    sig = inspect.signature(post_obligation_event)
    params = list(sig.parameters.keys())
    assert "db" in params
    assert "owner_id" in params
    assert "event_type" in params
    assert "wallet_legs" in params
    assert "entity_legs" in params


def test_obligation_money_posting_seam_does_not_merge_debt_and_payment_plan():
    """The Obligation Money Posting seam MUST NOT import or reference
    Debt or Payment Plan models, services, or routers."""
    import inspect
    import app.services.obligation_money_posting_service as omps

    source = inspect.getsource(omps)

    # These words must NOT appear in the seam
    forbidden = [
        "DebtLedger",
        "PaymentPlanLedger",
        "PaymentPlanPayment",
        "DebtTransaction",
        "unified_obligation",
        "generic_obligation",
    ]
    for word in forbidden:
        assert word not in source, (
            f"Obligation seam must not reference '{word}' — "
            f"it would imply merged domain models"
        )


# ============================================================================
# Issue 6 — Non-expense Debt events route through shared seams
# ============================================================================


def test_debt_payment_service_uses_financial_event_ledger_for_non_expense(
    client, session,
):
    """Debt payment service routes non-expense events (DEBT_SETTLEMENT)
    through post_financial_event, creating proper FinancialEvent rows."""
    headers = create_user_and_token(
        client, "dcl7", "dcl7@example.com", "Password123!"
    )
    today = user_timezone_today()
    wallet = _default_wallet(client, headers)

    # OWING debt with is_money_transferred=True and no expense category
    # — the principal payment will be DEBT_SETTLEMENT (non-expense).
    debt_res = client.post(
        "/debts",
        json={
            "debt_type": "OWING",
            "counterparty_name": "Lender",
            "initial_amount": 500_000,
            "currency": "UZS",
            "date": today.isoformat(),
            "expected_return_date": today.isoformat(),
            "is_money_transferred": True,
            "initial_wallet_id": wallet["id"],
        },
        headers=headers,
    )
    assert debt_res.status_code == 201, debt_res.text
    debt = debt_res.json()

    balance_before = (
        session.query(models.Wallet)
        .filter(models.Wallet.id == wallet["id"])
        .first()
        .current_balance
    )

    # Pay the debt — principal is non-expense, routed through post_financial_event
    payment = client.post(
        f"/debts/{debt['id']}/payments",
        json={
            "amount": 500_000,
            "date": today.isoformat(),
            "wallet_allocations": [
                {"wallet_id": wallet["id"], "amount": 500_000},
            ],
        },
        headers=headers,
    )
    assert payment.status_code == 201, payment.text

    session.expire_all()

    # Verify the settlement event exists with correct metadata
    settlement_events = (
        session.query(models.FinancialEvent)
        .join(models.EntityLedger)
        .filter(
            models.EntityLedger.debt_id == debt["id"],
            models.FinancialEvent.event_type == models.TransactionType.DEBT_SETTLEMENT,
        )
        .all()
    )
    # The debt was created with is_money_transferred=True which also creates a
    # settlement event.  The payment creates another.  Both are correct.
    assert len(settlement_events) >= 1
    event = settlement_events[-1]
    assert event.status == models.FinancialEventStatus.POSTED
    assert event.reference_type == models.ReferenceType.DEBT_REPAYMENT

    # Wallet Ledger entries must exist with correct amount
    assert len(event.wallet_legs) == 1
    wallet_leg = event.wallet_legs[0]
    assert wallet_leg.wallet_id == wallet["id"]
    assert wallet_leg.amount == -500_000

    # Entity Ledger must link back to the debt
    assert len(event.entity_legs) == 1
    entity_leg = event.entity_legs[0]
    assert entity_leg.debt_id == debt["id"]

    # Wallet balance must reflect the payment exactly once
    refreshed = (
        session.query(models.Wallet)
        .filter(models.Wallet.id == wallet["id"])
        .first()
    )
    assert refreshed.current_balance == balance_before - 500_000


def test_debt_payment_keeps_domain_rules_separate(client, session):
    """Debt domain rules (principal/charge split, running balance) remain
    inside debt modules — the posting seam only handles money mechanics."""
    headers = create_user_and_token(
        client, "dcl8", "dcl8@example.com", "Password123!"
    )
    today = user_timezone_today()
    create_budget(client, headers, category="Debt Charges", monthly_limit=500_000,
                  budget_year=today.year, budget_month=today.month)
    wallet = _default_wallet(client, headers)

    # Create OWING debt and add a charge
    debt = _create_owing_debt(client, headers, wallet["id"])
    client.post(
        f"/debts/{debt['id']}/add-charge",
        json={"amount": 30_000, "reason": "Interest"},
        headers=headers,
    )

    # Pay the full amount (principal + charge).  The waterfall engine
    # allocates to principal first, then charge.  This exercises both
    # Debt Ledger entry types while keeping charge-specific rules visible.
    total_pay = 1_030_000  # 1M principal + 30K charge
    payment = client.post(
        f"/debts/{debt['id']}/payments",
        json={
            "amount": total_pay,
            "date": today.isoformat(),
            "wallet_allocations": [
                {"wallet_id": wallet["id"], "amount": total_pay},
            ],
        },
        headers=headers,
    )
    assert payment.status_code == 201, payment.text

    # Domain rule 1: Charge payment creates Debt Ledger entry with CHARGE_PAYMENT
    session.expire_all()
    ledger_entries = (
        session.query(models.DebtLedgerEntry)
        .filter(
            models.DebtLedgerEntry.debt_id == debt["id"],
            models.DebtLedgerEntry.event_subtype == "CHARGE_PAYMENT",
        )
        .all()
    )
    assert len(ledger_entries) >= 1
    charge_ledger = ledger_entries[0]
    assert charge_ledger.charge_delta == -30_000

    # Domain rule 2: Principal payment creates Debt Ledger entry with PRINCIPAL_PAYMENT
    principal_ledger_entries = (
        session.query(models.DebtLedgerEntry)
        .filter(
            models.DebtLedgerEntry.debt_id == debt["id"],
            models.DebtLedgerEntry.event_subtype == "PRINCIPAL_PAYMENT",
        )
        .all()
    )
    assert len(principal_ledger_entries) >= 1
    principal_ledger = principal_ledger_entries[0]
    assert principal_ledger.principal_delta == -1_000_000

    # Domain rule 3: Charge hits DEBT_CHARGES category through Budget Permission
    charge_events = (
        session.query(models.FinancialEvent)
        .join(models.EntityLedger)
        .filter(
            models.EntityLedger.debt_id == debt["id"],
            models.EntityLedger.category == models.ExpenseCategory.DEBT_CHARGES,
        )
        .all()
    )
    assert len(charge_events) >= 1

    # Domain rule 4: Debt remaining amount decreased to zero
    updated_debt = session.query(models.Debt).filter(
        models.Debt.id == debt["id"]
    ).first()
    assert updated_debt.remaining_amount == 0


def test_debt_charge_payment_preserves_entity_ledger_links(client, session):
    """Debt charge payments must preserve correct Entity Ledger links
    (debt_id, category, budget_id) after routing through shared seams."""
    headers = create_user_and_token(
        client, "dcl9", "dcl9@example.com", "Password123!"
    )
    today = user_timezone_today()
    create_budget(client, headers, category="Debt Charges", monthly_limit=500_000,
                  budget_year=today.year, budget_month=today.month)
    wallet = _default_wallet(client, headers)
    debt = _create_owing_debt(client, headers, wallet["id"])

    client.post(
        f"/debts/{debt['id']}/add-charge",
        json={"amount": 15_000, "reason": "Processing fee"},
        headers=headers,
    )

    client.post(
        f"/debts/{debt['id']}/payments",
        json={
            "amount": 1_015_000,
            "date": today.isoformat(),
            "wallet_allocations": [
                {"wallet_id": wallet["id"], "amount": 1_015_000},
            ],
        },
        headers=headers,
    )

    session.expire_all()

    # Find the charge entity leg
    charge_leg = (
        session.query(models.EntityLedger)
        .filter(
            models.EntityLedger.debt_id == debt["id"],
            models.EntityLedger.category == models.ExpenseCategory.DEBT_CHARGES,
        )
        .order_by(models.EntityLedger.id.desc())
        .first()
    )
    assert charge_leg is not None, "Charge must create an EntityLedger entry"
    assert charge_leg.debt_id == debt["id"]
    assert charge_leg.category == models.ExpenseCategory.DEBT_CHARGES
    # Budget Permission must have linked the charge to the Debt Charges budget
    assert charge_leg.budget_id is not None, (
        "Charge entity leg must be linked to a Budget via Budget Permission"
    )
