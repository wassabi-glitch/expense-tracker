"""Regression tests for Issue 3: Route Payment Plan expense posting through
the Expense Posting / FinancialEventLedger seam.

Verifies that recording a payment plan payment still produces correct
FinancialEvent, WalletLedger, and EntityLedger entries — without asserting
private helper call order.
"""

from app import models
from tests.helpers import create_budget, create_user_and_token, user_timezone_today


def _default_wallet(client, headers):
    response = client.get("/wallets", headers=headers)
    assert response.status_code == 200, response.text
    return response.json()[0]


def _create_plan(client, headers, **overrides):
    payload = {
        "item_name": "Test Phone",
        "store_or_bank_name": "Test Store",
        "total_price": 1_200_000,
        "down_payment": 0,
        "months": 12,
        "frequency": "MONTHLY",
        "start_date": user_timezone_today().isoformat(),
        "expense_category": "Electronics",
    }
    payload.update(overrides)
    res = client.post("/payment-plans", json=payload, headers=headers)
    assert res.status_code == 201, res.text
    return res.json()


def _budgets_for_plan(client, headers):
    today = user_timezone_today()
    create_budget(client, headers, category="Electronics", monthly_limit=9_000_000,
                  budget_year=today.year, budget_month=today.month)
    create_budget(client, headers, category="Debt Charges", monthly_limit=1_000_000,
                  budget_year=today.year, budget_month=today.month)


# ---------------------------------------------------------------------------
# Payment plan payment → FinancialEventLedger seam
# ---------------------------------------------------------------------------


def test_record_payment_creates_posted_financial_event(client, session):
    """Recording a payment plan payment creates a posted expense-shaped
    FinancialEvent through the ledger seam."""
    headers = create_user_and_token(
        client, "ppregress1", "ppregress1@example.com", "Password123!"
    )
    _budgets_for_plan(client, headers)
    wallet = _default_wallet(client, headers)
    plan = _create_plan(client, headers)

    payment = plan["payments"][0]
    res = client.post(
        f"/payment-plans/{plan['id']}/payments",
        json={
            "amount": payment["amount"],
            "paid_date": user_timezone_today().isoformat(),
            "wallet_allocations": [
                {"wallet_id": wallet["id"], "amount": payment["amount"]}
            ],
        },
        headers=headers,
    )
    assert res.status_code == 201, res.text

    session.expire_all()
    # Find the financial event created for this payment
    entity_leg = (
        session.query(models.EntityLedger)
        .filter(
            models.EntityLedger.payment_plan_id == plan["id"],
        )
        .order_by(models.EntityLedger.id.desc())
        .first()
    )
    assert entity_leg is not None
    event = (
        session.query(models.FinancialEvent)
        .filter(models.FinancialEvent.id == entity_leg.event_id)
        .first()
    )
    assert event is not None
    assert event.event_type == models.TransactionType.EXPENSE
    assert event.status == models.FinancialEventStatus.POSTED
    assert event.reference_type == models.ReferenceType.PAYMENT_PLAN_PAYMENT


def test_payment_plan_payment_writes_wallet_ledger(client, session):
    """Payment plan payments debit the selected wallet exactly once with
    correct funding classification."""
    headers = create_user_and_token(
        client, "ppregress2", "ppregress2@example.com", "Password123!"
    )
    _budgets_for_plan(client, headers)
    wallet = _default_wallet(client, headers)
    plan = _create_plan(client, headers)

    payment = plan["payments"][0]
    res = client.post(
        f"/payment-plans/{plan['id']}/payments",
        json={
            "amount": payment["amount"],
            "paid_date": user_timezone_today().isoformat(),
            "wallet_allocations": [
                {"wallet_id": wallet["id"], "amount": payment["amount"]}
            ],
        },
        headers=headers,
    )
    assert res.status_code == 201, res.text

    session.expire_all()
    entity_leg = (
        session.query(models.EntityLedger)
        .filter(models.EntityLedger.payment_plan_id == plan["id"])
        .order_by(models.EntityLedger.id.desc())
        .first()
    )
    event = (
        session.query(models.FinancialEvent)
        .filter(models.FinancialEvent.id == entity_leg.event_id)
        .first()
    )
    assert len(event.wallet_legs) == 1
    leg = event.wallet_legs[0]
    assert leg.wallet_id == wallet["id"]
    assert leg.amount == -payment["amount"]
    assert leg.owned_spend_amount is not None
    assert leg.borrowed_spend_amount is not None


def test_payment_plan_payment_preserves_entity_links(client, session):
    """Entity Ledger entries preserve payment_plan_id, category, and budget
    links."""
    headers = create_user_and_token(
        client, "ppregress3", "ppregress3@example.com", "Password123!"
    )
    _budgets_for_plan(client, headers)
    wallet = _default_wallet(client, headers)
    plan = _create_plan(client, headers)

    payment = plan["payments"][0]
    res = client.post(
        f"/payment-plans/{plan['id']}/payments",
        json={
            "amount": payment["amount"],
            "paid_date": user_timezone_today().isoformat(),
            "wallet_allocations": [
                {"wallet_id": wallet["id"], "amount": payment["amount"]}
            ],
        },
        headers=headers,
    )
    assert res.status_code == 201, res.text

    session.expire_all()
    entity_leg = (
        session.query(models.EntityLedger)
        .filter(models.EntityLedger.payment_plan_id == plan["id"])
        .order_by(models.EntityLedger.id.desc())
        .first()
    )
    assert entity_leg is not None
    assert entity_leg.payment_plan_id == plan["id"]
    assert entity_leg.category == models.ExpenseCategory.ELECTRONICS
    assert entity_leg.budget_id is not None


def test_payment_plan_payment_budget_required_failure(client, session):
    """Budget-required failure remains structured when category has no Budget."""
    headers = create_user_and_token(
        client, "ppregress4", "ppregress4@example.com", "Password123!"
    )
    wallet = _default_wallet(client, headers)
    # Deliberately skip creating a budget
    plan = _create_plan(client, headers)

    payment = plan["payments"][0]
    res = client.post(
        f"/payment-plans/{plan['id']}/payments",
        json={
            "amount": payment["amount"],
            "paid_date": user_timezone_today().isoformat(),
            "wallet_allocations": [
                {"wallet_id": wallet["id"], "amount": payment["amount"]}
            ],
        },
        headers=headers,
    )
    assert res.status_code == 400
    assert res.json()["detail"] == "expenses.budget_required"


def test_payment_plan_payment_future_date_rejected(client, session):
    """Future-date validation still uses the user's effective timezone."""
    headers = create_user_and_token(
        client, "ppregress5", "ppregress5@example.com", "Password123!"
    )
    _budgets_for_plan(client, headers)
    wallet = _default_wallet(client, headers)
    plan = _create_plan(client, headers)

    from datetime import date, timedelta
    future_date = user_timezone_today() + timedelta(days=30)

    payment = plan["payments"][0]
    res = client.post(
        f"/payment-plans/{plan['id']}/payments",
        json={
            "amount": payment["amount"],
            "paid_date": future_date.isoformat(),
            "wallet_allocations": [
                {"wallet_id": wallet["id"], "amount": payment["amount"]}
            ],
        },
        headers=headers,
    )
    assert res.status_code == 400
    assert "future" in res.json()["detail"].lower()


def test_payment_plan_payment_multi_wallet_allocation(client, session):
    """Multiple wallet allocations each produce a WalletLedger entry."""
    headers = create_user_and_token(
        client, "ppregress6", "ppregress6@example.com", "Password123!"
    )
    _budgets_for_plan(client, headers)
    wallet1 = _default_wallet(client, headers)

    # Create a second wallet
    wallet2_res = client.post(
        "/wallets",
        json={
            "name": "Second pocket",
            "wallet_type": "CASH",
            "initial_balance": 500_000,
        },
        headers=headers,
    )
    assert wallet2_res.status_code == 201, wallet2_res.text
    wallet2 = wallet2_res.json()

    plan = _create_plan(client, headers)
    payment = plan["payments"][0]
    half = payment["amount"] // 2
    remainder = payment["amount"] - half

    res = client.post(
        f"/payment-plans/{plan['id']}/payments",
        json={
            "amount": payment["amount"],
            "paid_date": user_timezone_today().isoformat(),
            "wallet_allocations": [
                {"wallet_id": wallet1["id"], "amount": half},
                {"wallet_id": wallet2["id"], "amount": remainder},
            ],
        },
        headers=headers,
    )
    assert res.status_code == 201, res.text

    session.expire_all()
    entity_leg = (
        session.query(models.EntityLedger)
        .filter(models.EntityLedger.payment_plan_id == plan["id"])
        .order_by(models.EntityLedger.id.desc())
        .first()
    )
    event = (
        session.query(models.FinancialEvent)
        .filter(models.FinancialEvent.id == entity_leg.event_id)
        .first()
    )
    assert len(event.wallet_legs) == 2
    wallet_ids = {leg.wallet_id for leg in event.wallet_legs}
    assert wallet1["id"] in wallet_ids
    assert wallet2["id"] in wallet_ids
    total_debit = sum(int(leg.amount) for leg in event.wallet_legs)
    assert total_debit == -payment["amount"]


def test_payment_plan_charge_payment_preserves_debt_charges_category(client, session):
    """Charge component payments preserve DEBT_CHARGES category in entity
    ledger links."""
    headers = create_user_and_token(
        client, "ppregress7", "ppregress7@example.com", "Password123!"
    )
    _budgets_for_plan(client, headers)
    wallet = _default_wallet(client, headers)

    # Create a plan and add a charge
    plan = _create_plan(client, headers)
    charge_res = client.post(
        f"/payment-plans/{plan['id']}/charges",
        json={
            "amount": 50_000,
            "charge_type": "FEE",
            "note": "Late fee",
        },
        headers=headers,
    )
    assert charge_res.status_code == 201, charge_res.text

    # Pay the charge
    updated_plan = charge_res.json()
    charge_payment = [
        p for p in updated_plan["payments"]
        if p["component_type"] == "CHARGE" and p["status"] == "PENDING"
    ][0]

    res = client.post(
        f"/payment-plans/{plan['id']}/payments",
        json={
            "amount": charge_payment["amount"],
            "paid_date": user_timezone_today().isoformat(),
            "wallet_allocations": [
                {"wallet_id": wallet["id"], "amount": charge_payment["amount"]}
            ],
        },
        headers=headers,
    )
    assert res.status_code == 201, res.text

    session.expire_all()
    charge_legs = (
        session.query(models.EntityLedger)
        .filter(
            models.EntityLedger.payment_plan_id == plan["id"],
            models.EntityLedger.category == models.ExpenseCategory.DEBT_CHARGES,
        )
        .order_by(models.EntityLedger.id.desc())
        .all()
    )
    assert len(charge_legs) >= 1
    charge_leg = charge_legs[0]
    assert charge_leg.budget_id is not None
    assert charge_leg.amount > 0


# ============================================================================
# Issue 7 — Payment Plan domain rules preserved through shared seams
# ============================================================================


def test_payment_plan_waterfall_charges_before_principal(client, session):
    """Payment Plan waterfall engine pays charge rows before principal rows.
    This domain rule must survive routing through shared posting seams."""
    headers = create_user_and_token(
        client, "ppissue7a", "ppissue7a@example.com", "Password123!"
    )
    today = user_timezone_today()
    _budgets_for_plan(client, headers)
    wallet = _default_wallet(client, headers)

    # Create a plan with a charge
    plan = _create_plan(client, headers)
    plan_id = plan["id"]

    client.post(
        f"/payment-plans/{plan_id}/charges",
        json={
            "amount": 50_000,
            "charge_type": "FEE",
            "note": "Origination fee",
        },
        headers=headers,
    )

    # Record payment large enough to cover charge + some principal.
    # The charge is 50K; total payment 150K covers charge + 100K principal.
    res = client.post(
        f"/payment-plans/{plan_id}/payments",
        json={
            "amount": 150_000,
            "paid_date": today.isoformat(),
            "wallet_allocations": [
                {"wallet_id": wallet["id"], "amount": 150_000},
            ],
        },
        headers=headers,
    )
    assert res.status_code == 201, res.text

    session.expire_all()

    # Waterfall rule: charge is paid before principal.  The charge component
    # appears in the DEBT_CHARGES Entity Ledger entries.
    charge_legs = (
        session.query(models.EntityLedger)
        .filter(
            models.EntityLedger.payment_plan_id == plan_id,
            models.EntityLedger.category == models.ExpenseCategory.DEBT_CHARGES,
        )
        .all()
    )
    assert len(charge_legs) >= 1, (
        "Charge must be paid via DEBT_CHARGES Entity Ledger entry"
    )
    total_charge_paid = sum(int(leg.amount) for leg in charge_legs)
    assert total_charge_paid == 50_000, (
        f"Charge amount 50_000 must be fully paid, got {total_charge_paid}"
    )

    # Principal rows must also be partially paid
    principal_legs = (
        session.query(models.EntityLedger)
        .filter(
            models.EntityLedger.payment_plan_id == plan_id,
            models.EntityLedger.category != models.ExpenseCategory.DEBT_CHARGES,
        )
        .all()
    )
    total_principal_paid = sum(int(leg.amount) for leg in principal_legs)
    assert total_principal_paid == 100_000, (
        f"Principal must receive remainder after charge: 100_000, got {total_principal_paid}"
    )

    # Verify Payment Plan Ledger entries reflect the charge payment
    ledger_entries = (
        session.query(models.PaymentPlanLedgerEntry)
        .filter(models.PaymentPlanLedgerEntry.plan_id == plan_id)
        .all()
    )
    # INITIAL entry + payment entry (covering both charge and principal)
    assert len(ledger_entries) >= 2


def test_payment_plan_domain_rules_remain_separate_from_debt(client, session):
    """Payment Plan retains its own models (PaymentPlan, PaymentPlanPayment,
    PaymentPlanLedgerEntry) — no Debt concepts leak in."""
    headers = create_user_and_token(
        client, "ppissue7b", "ppissue7b@example.com", "Password123!"
    )
    today = user_timezone_today()
    _budgets_for_plan(client, headers)
    wallet = _default_wallet(client, headers)

    plan = _create_plan(client, headers)
    plan_id = plan["id"]

    res = client.post(
        f"/payment-plans/{plan_id}/payments",
        json={
            "amount": 200_000,
            "paid_date": today.isoformat(),
            "wallet_allocations": [
                {"wallet_id": wallet["id"], "amount": 200_000},
            ],
        },
        headers=headers,
    )
    assert res.status_code == 201, res.text

    session.expire_all()

    # Payment Plan must use its own ledger, NOT Debt ledger
    pp_ledger = (
        session.query(models.PaymentPlanLedgerEntry)
        .filter(models.PaymentPlanLedgerEntry.plan_id == plan_id)
        .all()
    )
    assert len(pp_ledger) >= 1, "Payment Plan must create PaymentPlanLedgerEntry"

    # No DebtLedgerEntry should reference the payment plan
    debt_ledger = (
        session.query(models.DebtLedgerEntry)
        .filter(models.DebtLedgerEntry.debt_id.isnot(None))
        .all()
    )
    # The payment plan payment should NOT create Debt ledger entries
    pp_debt_ledger = [
        e for e in debt_ledger
        if e.note and "payment_plan" in (e.note or "").lower()
    ]
    assert len(pp_debt_ledger) == 0, (
        "Payment Plan payments must not create Debt Ledger entries"
    )

    # Payment Plan must NOT create Debt rows
    debts = (
        session.query(models.Debt)
        .filter(models.Debt.owner_id == session.query(models.User)
                .filter(models.User.email == "ppissue7b@example.com")
                .first().id)
        .all()
    )
    plan_related_debts = [
        d for d in debts
        if d.description and "payment_plan" in (d.description or "").lower()
    ]
    assert len(plan_related_debts) == 0, (
        "Payment Plan must not create Debt rows"
    )


def test_payment_plan_ledger_entries_preserved_through_seam(client, session):
    """Payment Plan Ledger entries remain correct (amount, plan_id link,
    transaction link) after routing through shared posting seams."""
    headers = create_user_and_token(
        client, "ppissue7c", "ppissue7c@example.com", "Password123!"
    )
    today = user_timezone_today()
    _budgets_for_plan(client, headers)
    wallet = _default_wallet(client, headers)

    plan = _create_plan(client, headers)
    plan_id = plan["id"]

    client.post(
        f"/payment-plans/{plan_id}/charges",
        json={
            "amount": 30_000,
            "charge_type": "FEE",
            "note": "Service fee",
        },
        headers=headers,
    )

    res = client.post(
        f"/payment-plans/{plan_id}/payments",
        json={
            "amount": 300_000,
            "paid_date": today.isoformat(),
            "wallet_allocations": [
                {"wallet_id": wallet["id"], "amount": 300_000},
            ],
        },
        headers=headers,
    )
    assert res.status_code == 201, res.text

    session.expire_all()

    # Payment Plan Ledger entries must exist with correct metadata
    ledger_entries = (
        session.query(models.PaymentPlanLedgerEntry)
        .filter(models.PaymentPlanLedgerEntry.plan_id == plan_id)
        .order_by(models.PaymentPlanLedgerEntry.id.asc())
        .all()
    )
    assert len(ledger_entries) >= 1

    for entry in ledger_entries:
        assert entry.plan_id == plan_id
        assert entry.amount_delta != 0
        # Each ledger entry should link to a Financial Event
        if entry.financial_event_id is not None:
            event = session.query(models.FinancialEvent).filter(
                models.FinancialEvent.id == entry.financial_event_id
            ).first()
            assert event is not None
            assert event.status == models.FinancialEventStatus.POSTED

    # Payment Plan Transaction must link to wallet allocations
    transactions = (
        session.query(models.PaymentPlanTransaction)
        .filter(models.PaymentPlanTransaction.plan_id == plan_id)
        .all()
    )
    assert len(transactions) >= 1
    assert sum(int(t.amount) for t in transactions) == 300_000
