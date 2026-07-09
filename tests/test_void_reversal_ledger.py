"""Regression tests for Issue 5: Move expense void and reversal mechanics
behind the FinancialEventLedger seam.

Verifies that voiding a posted expense creates a correctly-shaped reversal
through the ledger seam without asserting private helper call order.
"""

from app import models
from app.domains.ledger import void_financial_event
from app.services.expense_posting_service import post_expense_event
from app.timezone import resolve_effective_timezone
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


# ---------------------------------------------------------------------------
# Shared void_financial_event seam — direct call tests
# ---------------------------------------------------------------------------


def test_shared_void_preserves_original_event(client, session):
    """Ticket 1: The shared void_financial_event function preserves the
    original FinancialEvent instead of deleting it."""
    headers = create_user_and_token(
        client, "sharedvoid1", "sharedvoid1@example.com", "Password123!"
    )
    create_budget(client, headers, category="Groceries", monthly_limit=500_000)
    user = session.query(models.User).filter(models.User.email == "sharedvoid1@example.com").first()

    result = post_expense_event(
        session,
        user.id,
        title="Shared void test",
        amount=15_000,
        category=models.ExpenseCategory.GROCERIES,
        expense_date=user_timezone_today(),
    )
    event_id = result.event.id
    session.commit()

    user_tz = resolve_effective_timezone(x_timezone="Asia/Tashkent")

    void_financial_event(
        session,
        event=result.event,
        owner_id=user.id,
        user_tz=user_tz,
        void_reason="Test void",
    )
    session.commit()

    session.expire_all()
    original = session.query(models.FinancialEvent).filter(models.FinancialEvent.id == event_id).first()
    assert original is not None, "Original event must still exist after voiding"
    assert original.status == models.FinancialEventStatus.VOIDED
    assert original.void_reversal_event_id is not None
    assert original.void_reason == "Test void"


def test_shared_void_appends_reversal_with_counter_balancing_legs(client, session):
    """Ticket 1: void_financial_event appends a reversal event with
    counter-balancing wallet and entity ledger effects."""
    headers = create_user_and_token(
        client, "sharedvoid2", "sharedvoid2@example.com", "Password123!"
    )
    create_budget(client, headers, category="Transport", monthly_limit=500_000)
    user = session.query(models.User).filter(models.User.email == "sharedvoid2@example.com").first()

    result = post_expense_event(
        session,
        user.id,
        title="Counter-balance test",
        amount=25_000,
        category=models.ExpenseCategory.TRANSPORT,
        expense_date=user_timezone_today(),
    )
    original_event_id = result.event.id
    session.commit()

    user_tz = resolve_effective_timezone(x_timezone="Asia/Tashkent")

    reversal = void_financial_event(
        session,
        event=result.event,
        owner_id=user.id,
        user_tz=user_tz,
    )
    session.commit()

    assert reversal.status == models.FinancialEventStatus.REVERSAL
    assert reversal.reference_type == models.ReferenceType.VOID_REVERSAL
    assert reversal.reverses_event_id == original_event_id
    assert reversal.linked_event_id == original_event_id

    # Wallet legs counter-balance
    assert len(reversal.wallet_legs) == len(result.event.wallet_legs)
    for orig_leg in result.event.wallet_legs:
        rev_leg = next(
            (leg for leg in reversal.wallet_legs if leg.wallet_id == orig_leg.wallet_id),
            None,
        )
        assert rev_leg is not None
        assert rev_leg.amount == -orig_leg.amount, (
            f"Reversal amount {rev_leg.amount} must counter-balance {orig_leg.amount}"
        )

    # Entity legs counter-balance
    assert len(reversal.entity_legs) == len(result.event.entity_legs)
    for orig_leg in result.event.entity_legs:
        rev_leg = next(
            (leg for leg in reversal.entity_legs
             if leg.category == orig_leg.category),
            None,
        )
        assert rev_leg is not None
        assert rev_leg.amount == -orig_leg.amount


def test_shared_void_links_original_and_reversal_for_audit_trail(client, session):
    """Ticket 1: The original and reversal events are linked so the audit
    trail is explainable."""
    headers = create_user_and_token(
        client, "sharedvoid3", "sharedvoid3@example.com", "Password123!"
    )
    create_budget(client, headers, category="Dining Out", monthly_limit=500_000)
    user = session.query(models.User).filter(models.User.email == "sharedvoid3@example.com").first()

    result = post_expense_event(
        session,
        user.id,
        title="Audit trail test",
        amount=10_000,
        category=models.ExpenseCategory.DINING_OUT,
        expense_date=user_timezone_today(),
    )
    session.commit()

    user_tz = resolve_effective_timezone(x_timezone="Asia/Tashkent")
    reversal = void_financial_event(
        session,
        event=result.event,
        owner_id=user.id,
        user_tz=user_tz,
    )
    session.commit()

    # Original → Reversal
    assert result.event.void_reversal_event_id == reversal.id
    # Reversal → Original
    assert reversal.reverses_event_id == result.event.id
    # Reversal linked to original
    assert reversal.linked_event_id == result.event.id


def test_shared_void_rejects_second_void_attempt(client, session):
    """Ticket 1: A second void attempt on the same posted event is rejected
    with clear behavior."""
    headers = create_user_and_token(
        client, "sharedvoid4", "sharedvoid4@example.com", "Password123!"
    )
    create_budget(client, headers, category="Groceries", monthly_limit=500_000)
    user = session.query(models.User).filter(models.User.email == "sharedvoid4@example.com").first()

    result = post_expense_event(
        session,
        user.id,
        title="Double void test",
        amount=5_000,
        category=models.ExpenseCategory.GROCERIES,
        expense_date=user_timezone_today(),
    )
    session.commit()

    user_tz = resolve_effective_timezone(x_timezone="Asia/Tashkent")

    # First void succeeds
    void_financial_event(
        session,
        event=result.event,
        owner_id=user.id,
        user_tz=user_tz,
    )
    session.commit()

    # Second void must be rejected
    from app.domains.ledger import EventNotPostedError
    try:
        void_financial_event(
            session,
            event=result.event,
            owner_id=user.id,
            user_tz=user_tz,
        )
        assert False, "Second void attempt should have raised"
    except EventNotPostedError as exc:
        assert exc.detail == "ledger.event_not_posted"


def test_shared_void_wallet_math_returns_to_expected_balance(client, session):
    """Ticket 1: Wallet math returns to the expected balance after reversal."""
    headers = create_user_and_token(
        client, "sharedvoid5", "sharedvoid5@example.com", "Password123!"
    )
    create_budget(client, headers, category="Groceries", monthly_limit=500_000)
    user = session.query(models.User).filter(models.User.email == "sharedvoid5@example.com").first()

    wallet = (
        session.query(models.Wallet)
        .filter(models.Wallet.owner_id == user.id, models.Wallet.is_default)
        .first()
    )
    balance_before = wallet.current_balance

    result = post_expense_event(
        session,
        user.id,
        title="Balance restore test",
        amount=50_000,
        category=models.ExpenseCategory.GROCERIES,
        expense_date=user_timezone_today(),
    )
    session.commit()

    session.expire_all()
    wallet_after_expense = session.query(models.Wallet).filter(models.Wallet.id == wallet.id).first()
    assert wallet_after_expense.current_balance == balance_before - 50_000

    user_tz = resolve_effective_timezone(x_timezone="Asia/Tashkent")
    void_financial_event(
        session,
        event=result.event,
        owner_id=user.id,
        user_tz=user_tz,
    )
    session.commit()

    session.expire_all()
    wallet_after_void = session.query(models.Wallet).filter(models.Wallet.id == wallet.id).first()
    assert wallet_after_void.current_balance == balance_before, (
        f"Balance after void ({wallet_after_void.current_balance}) "
        f"must equal balance before expense ({balance_before})"
    )


def test_metadata_only_edit_does_not_create_reversal(client, session):
    """Ticket 1: Metadata-only fields (title, description) remain editable
    without creating a reversal."""
    headers = create_user_and_token(
        client, "sharedvoid6", "sharedvoid6@example.com", "Password123!"
    )
    create_budget(client, headers, category="Groceries", monthly_limit=500_000)

    created = client.post(
        "/expenses/",
        json={
            "title": "Original Title",
            "amount": 20_000,
            "category": "Groceries",
            "description": "Original description",
            "date": user_timezone_today().isoformat(),
        },
        headers=headers,
    )
    assert created.status_code == 201, created.text
    expense_id = created.json()["id"]

    # Metadata-only update: change title and description only
    updated = client.put(
        f"/expenses/{expense_id}",
        json={
            "title": "Updated Title",
            "description": "Updated description",
        },
        headers=headers,
    )
    assert updated.status_code == 200, updated.text

    session.expire_all()
    event = (
        session.query(models.FinancialEvent)
        .filter(models.FinancialEvent.id == expense_id)
        .first()
    )
    # Metadata changed
    assert event.title == "Updated Title"
    assert event.description == "Updated description"
    # Still posted — no void/reversal created for metadata-only edits
    assert event.status == models.FinancialEventStatus.POSTED
    assert event.void_reversal_event_id is None
