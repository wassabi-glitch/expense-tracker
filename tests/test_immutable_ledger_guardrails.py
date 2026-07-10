"""Immutable-ledger regression guardrails for new debt and payment-plan
Epicspart2 obligation work (Ticket 7).

These tests encode the contract from ADR-0024 and ADR-0025: posted Financial
Events must never be hard-deleted or mutated in place when wallet legs exist.
Metadata-only operations, planning intent, and draft state remain mutable.

The tests are black-box route-level assertions — they call HTTP endpoints and
check database invariants via the ``session`` fixture.  They do NOT fix existing
violations (those are conversion work for future tickets); they ensure that
*new* obligation work does not introduce more mutable money history.
"""

from app import models
from app.main import app
from app.session import get_db
from tests.helpers import create_budget, create_user_and_token, user_timezone_today


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------


def _default_wallet(client, headers):
    response = client.get("/wallets", headers=headers)
    assert response.status_code == 200, response.text
    wallets = response.json()
    assert len(wallets) > 0
    return wallets[0]


def _create_transferred_debt(client, headers, wallet_id, **overrides):
    """Create an OWING debt with is_money_transferred=True (wallet legs exist)."""
    payload: dict = {
        "debt_type": "OWING",
        "counterparty_name": "Bank loan",
        "initial_amount": 1_000_000,
        "currency": "UZS",
        "date": user_timezone_today().isoformat(),
        "expected_return_date": user_timezone_today().isoformat(),
        "is_money_transferred": True,
        "initial_wallet_id": wallet_id,
    }
    payload.update(overrides)
    response = client.post("/debts", json=payload, headers=headers)
    assert response.status_code == 201, response.text
    return response.json()


def _create_non_money_debt(client, headers, **overrides):
    """Create an OWING debt with is_money_transferred=False (no wallet legs).
    This is a planning-intent / metadata-only obligation."""
    payload: dict = {
        "debt_type": "OWING",
        "counterparty_name": "Mom",
        "initial_amount": 150_000,
        "currency": "UZS",
        "description": "Dinner",
        "date": user_timezone_today().isoformat(),
        "expected_return_date": user_timezone_today().isoformat(),
        "is_money_transferred": False,
        "expense_category": "Dining Out",
    }
    payload.update(overrides)
    response = client.post("/debts", json=payload, headers=headers)
    assert response.status_code == 201, response.text
    return response.json()


def _create_payment_plan(client, headers, **overrides):
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
    response = client.post("/payment-plans", json=payload, headers=headers)
    assert response.status_code == 201, response.text
    return response.json()


def _user(session, email):
    return session.query(models.User).filter(models.User.email == email).first()


def _make_user_premium(email):
    """Mark a test user as premium so recurring templates are allowed."""
    override_db_factory = app.dependency_overrides.get(get_db)
    if override_db_factory:
        db_gen = override_db_factory()
        db = next(db_gen)
        try:
            user = db.query(models.User).filter(models.User.email == email).first()
            if user:
                user.is_premium = True
                db.commit()
        finally:
            db.close()
            try:
                next(db_gen)
            except StopIteration:
                pass


def _financial_event_count(session, owner_id):
    return (
        session.query(models.FinancialEvent)
        .filter(models.FinancialEvent.owner_id == owner_id)
        .count()
    )


# =========================================================================
# Group A — Financial events survive reversals (checkbox 4)
# =========================================================================


def test_debt_ledger_reversal_preserves_financial_events(client, session):
    """Reversing a debt ledger entry that links to a FinancialEvent creates a
    REVERSAL FinancialEvent and preserves the original."""
    headers = create_user_and_token(
        client, "guardrail_a1", "guardrail_a1@example.com", "Password123!"
    )
    wallet = _default_wallet(client, headers)
    debt = _create_transferred_debt(client, headers, wallet["id"])

    # Make a payment to produce FinancialEvents and DebtLedgerEntries.
    payment = client.post(
        f"/debts/{debt['id']}/payments",
        json={
            "amount": 300_000,
            "date": user_timezone_today().isoformat(),
            "wallet_allocations": [{"wallet_id": wallet["id"], "amount": 300_000}],
        },
        headers=headers,
    )
    assert payment.status_code == 201, payment.text

    # Get the PAYMENT ledger entry that has a financial_event.
    detail = client.get(f"/debts/{debt['id']}", headers=headers)
    assert detail.status_code == 200, detail.text
    payment_entry = next(
        entry
        for entry in detail.json()["ledger_entries"]
        if entry["entry_type"] == "PAYMENT" and entry["financial_event_id"] is not None
    )
    original_event_id = payment_entry["financial_event_id"]

    # Reverse the ledger entry.
    rev = client.post(
        f"/debts/{debt['id']}/ledger/{payment_entry['id']}/reverse",
        json={"note": "Test reversal via guardrail"},
        headers=headers,
    )
    assert rev.status_code == 200, rev.text

    session.expire_all()

    # The original FinancialEvent must still exist.
    original_event = (
        session.query(models.FinancialEvent)
        .filter(models.FinancialEvent.id == original_event_id)
        .first()
    )
    assert original_event is not None, "Original FinancialEvent was hard-deleted"
    assert original_event.status == models.FinancialEventStatus.VOIDED

    # A linked REVERSAL FinancialEvent must exist.
    reversal_event = (
        session.query(models.FinancialEvent)
        .filter(models.FinancialEvent.id == original_event.void_reversal_event_id)
        .first()
    )
    assert reversal_event is not None, "No reversal FinancialEvent was created"
    assert reversal_event.status == models.FinancialEventStatus.REVERSAL
    assert reversal_event.reverses_event_id == original_event.id

    # A DebtLedgerEntry REVERSAL must exist with counter-balancing amounts.
    reversal_ledger = (
        session.query(models.DebtLedgerEntry)
        .filter(
            models.DebtLedgerEntry.debt_id == debt["id"],
            models.DebtLedgerEntry.entry_type == models.DebtLedgerEntryType.REVERSAL,
            models.DebtLedgerEntry.reverses_entry_id == payment_entry["id"],
        )
        .first()
    )
    assert reversal_ledger is not None, "No REVERSAL DebtLedgerEntry created"


def test_payment_plan_undo_preserves_financial_events(client, session):
    """Undoing a payment plan payment creates FinancialEvent reversals instead
    of hard-deleting the original events."""
    headers = create_user_and_token(
        client, "guardrail_a2", "guardrail_a2@example.com", "Password123!"
    )
    today = user_timezone_today()
    create_budget(
        client, headers, category="Electronics", monthly_limit=9_000_000,
        budget_year=today.year, budget_month=today.month,
    )
    create_budget(
        client, headers, category="Debt Charges", monthly_limit=1_000_000,
        budget_year=today.year, budget_month=today.month,
    )
    wallet = _default_wallet(client, headers)
    plan = _create_payment_plan(client, headers)

    # Record one payment.
    payment_row = plan["payments"][0]
    pay_res = client.post(
        f"/payment-plans/{plan['id']}/payments",
        json={
            "amount": payment_row["amount"],
            "paid_date": today.isoformat(),
            "wallet_allocations": [
                {"wallet_id": wallet["id"], "amount": payment_row["amount"]}
            ],
        },
        headers=headers,
    )
    assert pay_res.status_code == 201, pay_res.text

    # Collect the FinancialEvent IDs created by this payment.
    session.expire_all()
    entity_legs = (
        session.query(models.EntityLedger)
        .filter(
            models.EntityLedger.payment_plan_id == plan["id"],
        )
        .order_by(models.EntityLedger.id.desc())
        .limit(5)
        .all()
    )
    original_event_ids = {leg.event_id for leg in entity_legs}
    assert len(original_event_ids) > 0, "No FinancialEvents found for payment"

    # Undo the payment.
    undo_res = client.post(
        f"/payment-plans/{plan['id']}/payments/undo-latest",
        headers=headers,
    )
    assert undo_res.status_code == 200, undo_res.text

    session.expire_all()

    # Every original FinancialEvent must still exist.
    for event_id in original_event_ids:
        event = (
            session.query(models.FinancialEvent)
            .filter(models.FinancialEvent.id == event_id)
            .first()
        )
        assert event is not None, f"FinancialEvent {event_id} was hard-deleted by undo"
        # May be POSTED (untouched) or VOIDED if linked to a reversal.
        assert event.status in (
            models.FinancialEventStatus.POSTED,
            models.FinancialEventStatus.VOIDED,
        ), f"FinancialEvent {event_id} has unexpected status {event.status}"

    # At least one reversal FinancialEvent must exist.
    reversal_count = (
        session.query(models.FinancialEvent)
        .filter(
            models.FinancialEvent.owner_id == _user(session, "guardrail_a2@example.com").id,
            models.FinancialEvent.status == models.FinancialEventStatus.REVERSAL,
        )
        .count()
    )
    assert reversal_count >= 1, "No REVERSAL FinancialEvent created by undo"


# =========================================================================
# Group B — Immutable money facts vs mutable metadata (checkbox 5)
# =========================================================================


def test_debt_metadata_update_is_direct_mutation(client, session):
    """Updating debt metadata (counterparty_name, description) does NOT create
    new FinancialEvents or DebtLedgerEntry reversals."""
    headers = create_user_and_token(
        client, "guardrail_b1", "guardrail_b1@example.com", "Password123!"
    )
    wallet = _default_wallet(client, headers)
    debt = _create_transferred_debt(client, headers, wallet["id"])

    session.expire_all()
    user = _user(session, "guardrail_b1@example.com")
    events_before = _financial_event_count(session, user.id)
    ledger_before = (
        session.query(models.DebtLedgerEntry)
        .filter(models.DebtLedgerEntry.debt_id == debt["id"])
        .count()
    )

    # Update metadata only — counterparty_name and description.
    updated = client.patch(
        f"/debts/{debt['id']}",
        json={
            "counterparty_name": "Updated Bank",
            "description": "Metadata-only change",
        },
        headers=headers,
    )
    assert updated.status_code == 200, updated.text
    assert updated.json()["counterparty_name"] == "Updated Bank"
    assert updated.json()["description"] == "Metadata-only change"

    session.expire_all()
    events_after = _financial_event_count(session, user.id)
    ledger_after = (
        session.query(models.DebtLedgerEntry)
        .filter(models.DebtLedgerEntry.debt_id == debt["id"])
        .count()
    )

    # No new FinancialEvents or DebtLedgerEntries should be created.
    assert events_after == events_before, (
        f"Metadata update created {events_after - events_before} unexpected FinancialEvents"
    )
    assert ledger_after == ledger_before, (
        f"Metadata update created {ledger_after - ledger_before} unexpected DebtLedgerEntries"
    )


def test_debt_remaining_amount_is_projection(client, session):
    """debt.remaining_amount is a projection computed from DebtLedgerEntry rows,
    not a stored value that can diverge from the ledger."""
    headers = create_user_and_token(
        client, "guardrail_b2", "guardrail_b2@example.com", "Password123!"
    )
    wallet = _default_wallet(client, headers)
    debt = _create_transferred_debt(client, headers, wallet["id"])

    # After creation, remaining_amount == ledger sum.
    detail = client.get(f"/debts/{debt['id']}", headers=headers)
    assert detail.status_code == 200, detail.text
    payload = detail.json()
    assert payload["remaining_amount"] == 1_000_000
    assert payload["total_paid"] == 0

    # Add a charge — remaining_amount should increase.
    charge = client.post(
        f"/debts/{debt['id']}/add-charge",
        json={"amount": 50_000, "reason": "Late fee"},
        headers=headers,
    )
    assert charge.status_code == 201, charge.text
    detail = client.get(f"/debts/{debt['id']}", headers=headers)
    assert detail.json()["remaining_amount"] == 1_050_000
    assert detail.json()["total_charges"] == 50_000

    # Make a payment — remaining_amount should decrease.
    payment = client.post(
        f"/debts/{debt['id']}/payments",
        json={
            "amount": 200_000,
            "date": user_timezone_today().isoformat(),
            "wallet_allocations": [{"wallet_id": wallet["id"], "amount": 200_000}],
        },
        headers=headers,
    )
    assert payment.status_code == 201, payment.text
    detail = client.get(f"/debts/{debt['id']}", headers=headers)
    assert detail.json()["remaining_amount"] == 850_000
    assert detail.json()["total_paid"] == 200_000

    # Verify the projection matches the raw ledger sum.
    session.expire_all()
    ledger_sum = (
        session.query(models.DebtLedgerEntry)
        .filter(
            models.DebtLedgerEntry.debt_id == debt["id"],
            models.DebtLedgerEntry.status == "POSTED",
        )
        .with_entities(
            models.DebtLedgerEntry.amount_delta,
        )
        .all()
    )
    computed_remaining = sum(int(row[0]) for row in ledger_sum)
    assert detail.json()["remaining_amount"] == computed_remaining, (
        f"remaining_amount {detail.json()['remaining_amount']} != ledger sum {computed_remaining}"
    )

    # Reverse a ledger entry and verify projection recovers.
    payment_entry = next(
        entry
        for entry in detail.json()["ledger_entries"]
        if entry["entry_type"] == "PAYMENT"
    )
    rev = client.post(
        f"/debts/{debt['id']}/ledger/{payment_entry['id']}/reverse",
        json={"note": "Test projection recovery"},
        headers=headers,
    )
    assert rev.status_code == 200, rev.text

    session.expire_all()
    ledger_sum_after = sum(
        int(row[0])
        for row in session.query(models.DebtLedgerEntry.amount_delta)
        .filter(
            models.DebtLedgerEntry.debt_id == debt["id"],
            models.DebtLedgerEntry.status == "POSTED",
        )
        .all()
    )
    updated_detail = client.get(f"/debts/{debt['id']}", headers=headers)
    assert updated_detail.json()["remaining_amount"] == ledger_sum_after


def test_payment_plan_remaining_amount_is_projection(client, session):
    """plan.remaining_amount is a projection computed from
    PaymentPlanLedgerEntry rows."""
    headers = create_user_and_token(
        client, "guardrail_b3", "guardrail_b3@example.com", "Password123!"
    )
    today = user_timezone_today()
    create_budget(
        client, headers, category="Electronics", monthly_limit=9_000_000,
        budget_year=today.year, budget_month=today.month,
    )
    wallet = _default_wallet(client, headers)
    plan = _create_payment_plan(client, headers)

    # After creation: remaining_amount == total_price - down_payment.
    assert plan["remaining_amount"] == 1_200_000  # 1200000 - 0

    # Record a payment.
    payment_row = plan["payments"][0]
    pay_res = client.post(
        f"/payment-plans/{plan['id']}/payments",
        json={
            "amount": payment_row["amount"],
            "paid_date": today.isoformat(),
            "wallet_allocations": [
                {"wallet_id": wallet["id"], "amount": payment_row["amount"]}
            ],
        },
        headers=headers,
    )
    assert pay_res.status_code == 201, pay_res.text

    # Remaining amount should decrease.
    detail = client.get(f"/payment-plans/{plan['id']}/details", headers=headers)
    assert detail.status_code == 200, detail.text
    details_payload = detail.json()
    assert details_payload["plan"]["remaining_amount"] < 1_200_000

    # Verify the projection matches the ledger.
    # The INITIAL PaymentPlanLedgerEntry carries the starting remaining_amount
    # (positive amount_delta).  PAYMENT entries carry negative amount_delta.
    # remaining_amount = sum of all POSTED amount_delta entries.
    session.expire_all()
    ledger_sum = sum(
        int(row[0])
        for row in session.query(models.PaymentPlanLedgerEntry.amount_delta)
        .filter(
            models.PaymentPlanLedgerEntry.plan_id == plan["id"],
            models.PaymentPlanLedgerEntry.status == "POSTED",
        )
        .all()
    )
    assert details_payload["plan"]["remaining_amount"] == ledger_sum, (
        f"plan.remaining_amount {details_payload['plan']['remaining_amount']} "
        f"!= ledger sum {ledger_sum}"
    )


# =========================================================================
# Group C — Non-money entities stay out of the global financial ledger
#           (checkbox 6)
# =========================================================================


def test_budget_crud_does_not_create_financial_events(client, session):
    """Creating and deleting a budget must not create FinancialEvents.
    Budgets are spending permissions, not money movement."""
    headers = create_user_and_token(
        client, "guardrail_c1", "guardrail_c1@example.com", "Password123!"
    )
    today = user_timezone_today()
    user = _user(session, "guardrail_c1@example.com")

    events_before = _financial_event_count(session, user.id)

    # Create a budget.
    budget = client.post(
        "/budgets/",
        json={
            "category": "Groceries",
            "monthly_limit": 500_000,
            "budget_year": today.year,
            "budget_month": today.month,
        },
        headers=headers,
    )
    assert budget.status_code == 201, budget.text

    session.expire_all()
    events_after_create = _financial_event_count(session, user.id)
    assert events_after_create == events_before, (
        "Budget creation created unexpected FinancialEvent(s)"
    )

    # Delete the budget via the correct query-param endpoint.
    category_encoded = "Groceries"
    deleted = client.delete(
        f"/budgets/item?budget_year={today.year}&budget_month={today.month}"
        f"&category={category_encoded}",
        headers=headers,
    )
    assert deleted.status_code == 204, deleted.text

    session.expire_all()
    events_after_delete = _financial_event_count(session, user.id)
    assert events_after_delete == events_before, (
        "Budget deletion created unexpected FinancialEvent(s)"
    )


def test_recurring_template_delete_does_not_create_financial_events(client, session):
    """Deleting a recurring template must not create FinancialEvents.
    Templates are intent, not posted money."""
    headers = create_user_and_token(
        client, "guardrail_c2", "guardrail_c2@example.com", "Password123!"
    )
    _make_user_premium("guardrail_c2@example.com")
    user = _user(session, "guardrail_c2@example.com")

    create_budget(client, headers, category="Utilities", monthly_limit=500_000)

    events_before = _financial_event_count(session, user.id)

    # Create a recurring template.
    template = client.post(
        "/recurring/",
        json={
            "title": "Guardrail Template",
            "amount": 5_000,
            "category": "Utilities",
            "frequency": "MONTHLY",
            "start_date": user_timezone_today().isoformat(),
            "wallet_id": _default_wallet(client, headers)["id"],
        },
        headers=headers,
    )
    assert template.status_code == 201, template.text
    template_id = template.json()["id"]

    # Delete the template.
    deleted = client.delete(f"/recurring/{template_id}", headers=headers)
    assert deleted.status_code == 204

    session.expire_all()
    events_after = _financial_event_count(session, user.id)
    assert events_after == events_before, (
        f"Recurring template deletion created {events_after - events_before} "
        f"unexpected FinancialEvent(s)"
    )


def test_goal_lifecycle_does_not_create_wallet_ledger_entries(client, session):
    """Creating, archiving, and deleting a goal (with no contributions) must
    not create WalletLedger entries. Goals are reservations, not wallet
    movement."""
    headers = create_user_and_token(
        client, "guardrail_c3", "guardrail_c3@example.com", "Password123!"
    )
    _make_user_premium("guardrail_c3@example.com")

    # Onboard with a goal-funding wallet so goal creation succeeds.
    onboard = client.post(
        "/users/me/onboarding",
        json={
            "life_statuses": ["employed"],
            "wallets": [
                {
                    "name": "Savings",
                    "wallet_type": "SAVINGS",
                    "initial_balance": 2_000_000,
                    "can_fund_goals": True,
                }
            ],
        },
        headers=headers,
    )
    assert onboard.status_code == 200, onboard.text

    user = _user(session, "guardrail_c3@example.com")
    wallet_ledger_before = (
        session.query(models.WalletLedger)
        .filter(models.WalletLedger.owner_id == user.id)
        .count()
    )

    # Create a goal.
    goal = client.post(
        "/goals/",
        json={
            "title": "Guardrail Goal",
            "target_amount": 500_000,
            "target_date": user_timezone_today().isoformat(),
            "intent": "RESERVE",
        },
        headers=headers,
    )
    assert goal.status_code == 201, goal.text
    goal_id = goal.json()["id"]

    # Archive the goal (required before deletion).
    archived = client.post(f"/goals/{goal_id}/archive", headers=headers)
    assert archived.status_code == 200, archived.text

    # Delete the archived goal.
    deleted = client.delete(f"/goals/{goal_id}", headers=headers)
    assert deleted.status_code == 204, deleted.text

    session.expire_all()
    wallet_ledger_after = (
        session.query(models.WalletLedger)
        .filter(models.WalletLedger.owner_id == user.id)
        .count()
    )
    assert wallet_ledger_after == wallet_ledger_before, (
        f"Goal lifecycle created {wallet_ledger_after - wallet_ledger_before} "
        f"unexpected WalletLedger entries"
    )


def test_pristine_debt_without_money_is_directly_deletable(client, session):
    """Deleting a pristine non-money-transferred debt does not create
    FinancialEvents. No wallet movement means no immutable treatment needed."""
    headers = create_user_and_token(
        client, "guardrail_c4", "guardrail_c4@example.com", "Password123!"
    )
    create_budget(
        client, headers, category="Dining Out", monthly_limit=500_000,
        budget_year=user_timezone_today().year, budget_month=user_timezone_today().month,
    )
    user = _user(session, "guardrail_c4@example.com")

    debt = _create_non_money_debt(client, headers)
    events_before = _financial_event_count(session, user.id)

    deleted = client.delete(f"/debts/{debt['id']}", headers=headers)
    assert deleted.status_code == 204

    session.expire_all()
    events_after = _financial_event_count(session, user.id)
    assert events_after == events_before, (
        "Deleting pristine non-money debt created unexpected FinancialEvent(s)"
    )


def test_session_draft_lifecycle_does_not_create_financial_events(client, session):
    """Creating and deleting a session draft must not create FinancialEvents.
    Drafts are pre-posting intent, not posted money."""
    headers = create_user_and_token(
        client, "guardrail_c5", "guardrail_c5@example.com", "Password123!"
    )
    user = _user(session, "guardrail_c5@example.com")

    events_before = _financial_event_count(session, user.id)

    # Create a session draft (pre-posting intent).
    draft = client.post(
        "/expenses/session-drafts",
        json={
            "title": "Guardrail Draft",
            "description": "Test draft lifecycle",
            "date": user_timezone_today().isoformat(),
            "amount_paid": 10_000,
        },
        headers=headers,
    )
    assert draft.status_code == 201, draft.text
    draft_id = draft.json()["id"]

    # Delete the draft.
    deleted = client.delete(f"/expenses/session-drafts/{draft_id}", headers=headers)
    assert deleted.status_code == 204, deleted.text

    session.expire_all()
    events_after = _financial_event_count(session, user.id)
    assert events_after == events_before, (
        f"Session draft lifecycle created {events_after - events_before} "
        f"unexpected FinancialEvent(s)"
    )


# =========================================================================
# Group D — The wallet-legs boundary test (checkboxes 1-3)
# =========================================================================


def test_debt_with_wallet_transfer_has_posted_financial_event(client, session):
    """A debt with is_money_transferred=True creates a POSTED FinancialEvent
    with wallet legs — proving the wallet-legs boundary is enforced."""
    headers = create_user_and_token(
        client, "guardrail_d1", "guardrail_d1@example.com", "Password123!"
    )
    wallet = _default_wallet(client, headers)
    debt = _create_transferred_debt(client, headers, wallet["id"])

    session.expire_all()
    initial_event = (
        session.query(models.FinancialEvent)
        .join(models.EntityLedger, models.EntityLedger.event_id == models.FinancialEvent.id)
        .filter(
            models.EntityLedger.debt_id == debt["id"],
            models.FinancialEvent.reference_type == models.ReferenceType.DEBT_INITIAL,
        )
        .first()
    )
    assert initial_event is not None, (
        "Money-transferred debt must create a FinancialEvent"
    )
    assert initial_event.status == models.FinancialEventStatus.POSTED
    assert len(initial_event.wallet_legs) >= 1, (
        "Money-transferred debt FinancialEvent must have wallet legs"
    )
    assert initial_event.wallet_legs[0].amount != 0, (
        "Wallet leg amount must be non-zero for money-transferred debt"
    )


def test_debt_without_wallet_transfer_has_no_posted_wallet_events(client, session):
    """A debt with is_money_transferred=False has NO FinancialEvent with wallet
    legs — it is metadata/planning, not posted money."""
    headers = create_user_and_token(
        client, "guardrail_d2", "guardrail_d2@example.com", "Password123!"
    )
    create_budget(
        client, headers, category="Dining Out", monthly_limit=500_000,
        budget_year=user_timezone_today().year, budget_month=user_timezone_today().month,
    )
    debt = _create_non_money_debt(client, headers)

    session.expire_all()

    # A DebtLedgerEntry INITIAL exists for the obligation amount.
    initial_ledger = (
        session.query(models.DebtLedgerEntry)
        .filter(
            models.DebtLedgerEntry.debt_id == debt["id"],
            models.DebtLedgerEntry.entry_type == models.DebtLedgerEntryType.INITIAL,
        )
        .first()
    )
    assert initial_ledger is not None, "DebtLedgerEntry INITIAL must exist"

    # No FinancialEvent with wallet legs should exist for this debt.
    wallet_events = (
        session.query(models.FinancialEvent)
        .join(models.WalletLedger, models.WalletLedger.event_id == models.FinancialEvent.id)
        .join(models.EntityLedger, models.EntityLedger.event_id == models.FinancialEvent.id)
        .filter(models.EntityLedger.debt_id == debt["id"])
        .all()
    )
    assert len(wallet_events) == 0, (
        "Non-money-transferred debt must not create FinancialEvents with wallet legs"
    )


def test_debt_charge_uses_ledger_seam_for_payment(client, session):
    """When a debt charge is paid, the payment creates a FinancialEvent through
    the shared posting seam (post_expense_event for DEBT_CHARGES category)."""
    headers = create_user_and_token(
        client, "guardrail_d3", "guardrail_d3@example.com", "Password123!"
    )
    today = user_timezone_today()
    create_budget(
        client, headers, category="Debt Charges", monthly_limit=500_000,
        budget_year=today.year, budget_month=today.month,
    )
    wallet = _default_wallet(client, headers)
    debt = _create_transferred_debt(client, headers, wallet["id"])

    # Add a charge.
    charge = client.post(
        f"/debts/{debt['id']}/add-charge",
        json={"amount": 30_000, "reason": "Interest"},
        headers=headers,
    )
    assert charge.status_code == 201, charge.text

    # Pay the full amount (principal + charge).
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

    # The charge payment must produce a FinancialEvent through the ledger seam.
    charge_events = (
        session.query(models.FinancialEvent)
        .join(models.EntityLedger, models.EntityLedger.event_id == models.FinancialEvent.id)
        .filter(
            models.EntityLedger.debt_id == debt["id"],
            models.EntityLedger.category == models.ExpenseCategory.DEBT_CHARGES,
        )
        .all()
    )
    assert len(charge_events) >= 1, "Charge payment must create a FinancialEvent"
    for event in charge_events:
        assert event.status == models.FinancialEventStatus.POSTED
        # Each posted event must have wallet legs — proves the seam was used.
        assert len(event.wallet_legs) >= 1, (
            f"FinancialEvent {event.id} has no wallet legs — seam bypassed"
        )
        assert len(event.entity_legs) >= 1, (
            f"FinancialEvent {event.id} has no entity legs — seam bypassed"
        )
