"""Regression tests for the FinancialEventLedger seam (Issue 1 of PRD 1).

Coverage:
- Direct FinancialEventLedger module tests
- Expense Posting integration through the route
"""

from app import models
from app.services.expense_posting_service import post_expense_event
from app.services.financial_event_ledger_service import (
    PostEntityLeg,
    PostWalletLeg,
    post_financial_event,
)
from tests.helpers import (
    create_user_and_token,
    create_budget,
    user_timezone_today,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _seed_user_with_wallet(client, session, email: str) -> tuple[models.User, models.Wallet]:
    """Create a test user via the API and return their User + default Wallet."""
    headers = create_user_and_token(client, email.split("@")[0], email, "Password123!")
    user = session.query(models.User).filter(models.User.email == email).first()
    wallet = session.query(models.Wallet).filter(
        models.Wallet.owner_id == user.id,
        models.Wallet.is_default,
    ).first()
    return user, wallet


# ---------------------------------------------------------------------------
# Direct FinancialEventLedger tests
# ---------------------------------------------------------------------------


def test_post_financial_event_creates_posted_event(client, session):
    """Low-level seam creates one posted FinancialEvent with correct metadata."""
    user, wallet = _seed_user_with_wallet(client, session, "ledger1@example.com")

    event = post_financial_event(
        session,
        owner_id=user.id,
        title="Direct event",
        event_type=models.TransactionType.EXPENSE,
        date=user_timezone_today(),
        description="via ledger seam",
        reference_type="test_direct",
        entity_category=models.ExpenseCategory.GROCERIES,
        wallet_legs=[
            PostWalletLeg(wallet_id=wallet.id, amount=-50_000),
        ],
        entity_legs=[
            PostEntityLeg(
                label="Direct event",
                amount=50_000,
                category=models.ExpenseCategory.GROCERIES,
            ),
        ],
    )

    assert event.id is not None
    assert event.owner_id == user.id
    assert event.title == "Direct event"
    assert event.description == "via ledger seam"
    assert event.event_type == models.TransactionType.EXPENSE
    assert event.status == models.FinancialEventStatus.POSTED
    assert event.reference_type == "test_direct"
    assert event.is_session is False
    assert event.date == user_timezone_today()


def test_post_financial_event_writes_wallet_ledger_with_funding_classification(client, session):
    """WalletLedger entries capture owned/borrowed funding split at posting time."""
    user, wallet = _seed_user_with_wallet(client, session, "ledger2@example.com")
    balance_before = wallet.current_balance

    event = post_financial_event(
        session,
        owner_id=user.id,
        title="Funding test",
        event_type=models.TransactionType.EXPENSE,
        date=user_timezone_today(),
        entity_category=models.ExpenseCategory.TRANSPORT,
        wallet_legs=[
            PostWalletLeg(wallet_id=wallet.id, amount=-100_000),
        ],
        entity_legs=[
            PostEntityLeg(
                label="Funding test",
                amount=100_000,
                category=models.ExpenseCategory.TRANSPORT,
            ),
        ],
    )

    session.expire_all()
    event_from_db = session.query(models.FinancialEvent).filter(
        models.FinancialEvent.id == event.id,
    ).first()
    assert len(event_from_db.wallet_legs) == 1
    leg = event_from_db.wallet_legs[0]
    assert leg.wallet_id == wallet.id
    assert leg.amount == -100_000
    assert leg.owned_spend_amount == 100_000  # fully owned (balance > amount)
    assert leg.borrowed_spend_amount == 0

    refreshed = session.query(models.Wallet).filter(models.Wallet.id == wallet.id).first()
    assert refreshed.current_balance == balance_before - 100_000


def test_post_financial_event_supports_multi_wallet_allocation(client, session):
    """Multiple wallet legs debit each wallet exactly once."""
    user, default_wallet = _seed_user_with_wallet(client, session, "ledger3@example.com")

    second_wallet = models.Wallet(
        owner_id=user.id,
        name="Second pocket",
        wallet_type=models.WalletType.CASH,
        accounting_type=models.AccountingType.ASSET,
        initial_balance=500_000,
        current_balance=500_000,
        is_default=False,
    )
    session.add(second_wallet)
    session.commit()
    session.refresh(second_wallet)

    default_before = default_wallet.current_balance
    second_before = second_wallet.current_balance

    event = post_financial_event(
        session,
        owner_id=user.id,
        title="Multi wallet",
        event_type=models.TransactionType.EXPENSE,
        date=user_timezone_today(),
        entity_category=models.ExpenseCategory.GROCERIES,
        wallet_legs=[
            PostWalletLeg(wallet_id=default_wallet.id, amount=-60_000),
            PostWalletLeg(wallet_id=second_wallet.id, amount=-40_000),
        ],
        entity_legs=[
            PostEntityLeg(
                label="Multi wallet",
                amount=100_000,
                category=models.ExpenseCategory.GROCERIES,
            ),
        ],
    )

    session.expire_all()
    event_from_db = session.query(models.FinancialEvent).filter(
        models.FinancialEvent.id == event.id,
    ).first()
    assert len(event_from_db.wallet_legs) == 2
    assert sorted((leg.wallet_id, leg.amount) for leg in event_from_db.wallet_legs) == [
        (default_wallet.id, -60_000),
        (second_wallet.id, -40_000),
    ]
    refreshed_default = session.query(models.Wallet).filter(
        models.Wallet.id == default_wallet.id
    ).first()
    refreshed_second = session.query(models.Wallet).filter(
        models.Wallet.id == second_wallet.id
    ).first()
    assert refreshed_default.current_balance == default_before - 60_000
    assert refreshed_second.current_balance == second_before - 40_000


def test_post_financial_event_supports_multi_entity_legs(client, session):
    """Multiple entity legs preserve distinct labels, amounts, and categories."""
    user, wallet = _seed_user_with_wallet(client, session, "ledger4@example.com")

    event = post_financial_event(
        session,
        owner_id=user.id,
        title="Split receipt",
        event_type=models.TransactionType.EXPENSE,
        date=user_timezone_today(),
        entity_category=models.ExpenseCategory.GROCERIES,
        wallet_legs=[
            PostWalletLeg(wallet_id=wallet.id, amount=-200_000),
        ],
        entity_legs=[
            PostEntityLeg(
                label="Groceries",
                amount=120_000,
                category=models.ExpenseCategory.GROCERIES,
            ),
            PostEntityLeg(
                label="Cleaning",
                amount=80_000,
                category=models.ExpenseCategory.UTILITIES,
            ),
        ],
    )

    session.expire_all()
    event_from_db = session.query(models.FinancialEvent).filter(
        models.FinancialEvent.id == event.id,
    ).first()
    assert len(event_from_db.entity_legs) == 2
    assert sorted(
        (leg.label, int(leg.amount), leg.category) for leg in event_from_db.entity_legs
    ) == [
        ("Cleaning", 80_000, models.ExpenseCategory.UTILITIES),
        ("Groceries", 120_000, models.ExpenseCategory.GROCERIES),
    ]


def test_post_financial_event_preserves_entity_links(client, session):
    """EntityLedger entries preserve budget, subcategory, project, debt, and
    payment-plan links when supplied."""
    user, wallet = _seed_user_with_wallet(client, session, "ledger5@example.com")

    budget = models.Budget(
        owner_id=user.id,
        category=models.ExpenseCategory.GROCERIES,
        monthly_limit=1_000_000,
        budget_year=2026,
        budget_month=7,
    )
    session.add(budget)
    session.commit()
    session.refresh(budget)

    debt = models.Debt(
        owner_id=user.id,
        debt_type=models.DebtType.OWED,
        origin_kind=models.DebtOriginKind.SPLIT_REIMBURSEMENT,
        counterparty_kind=models.DebtCounterpartyKind.PERSON,
        product_kind=models.DebtProductKind.PERSONAL_REIMBURSEMENT,
        counterparty_name="Test contact",
        initial_amount=50_000,
        remaining_amount=50_000,
        currency="UZS",
        description="Test debt",
        status=models.DebtStatus.ACTIVE,
        date=user_timezone_today(),
        expected_return_date=user_timezone_today(),
    )
    session.add(debt)
    session.commit()
    session.refresh(debt)

    event = post_financial_event(
        session,
        owner_id=user.id,
        title="Linked entity",
        event_type=models.TransactionType.EXPENSE,
        date=user_timezone_today(),
        entity_category=models.ExpenseCategory.GROCERIES,
        wallet_legs=[
            PostWalletLeg(wallet_id=wallet.id, amount=-100_000),
        ],
        entity_legs=[
            PostEntityLeg(
                label="Linked entity",
                amount=100_000,
                category=models.ExpenseCategory.GROCERIES,
                budget_id=budget.id,
                debt_id=debt.id,
                payment_plan_id=None,
                payment_plan_payment_id=None,
            ),
        ],
    )

    session.expire_all()
    event_from_db = session.query(models.FinancialEvent).filter(
        models.FinancialEvent.id == event.id,
    ).first()
    leg = event_from_db.entity_legs[0]
    assert leg.budget_id == budget.id
    assert leg.debt_id == debt.id
    assert leg.payment_plan_id is None
    assert leg.payment_plan_payment_id is None


def test_post_financial_event_supports_non_posted_status(client, session):
    """The ledger seam supports explicit status for reversals and other flows."""
    user, wallet = _seed_user_with_wallet(client, session, "ledger6@example.com")

    event = post_financial_event(
        session,
        owner_id=user.id,
        title="Reversal event",
        event_type=models.TransactionType.EXPENSE,
        date=user_timezone_today(),
        status=models.FinancialEventStatus.REVERSAL,
        reference_type=models.ReferenceType.VOID_REVERSAL,
        entity_category=models.ExpenseCategory.GROCERIES,
        wallet_legs=[
            PostWalletLeg(wallet_id=wallet.id, amount=100_000),
        ],
        entity_legs=[
            PostEntityLeg(
                label="Reversal entity",
                amount=-100_000,
                category=models.ExpenseCategory.GROCERIES,
            ),
        ],
    )

    assert event.status == models.FinancialEventStatus.REVERSAL
    assert event.reference_type == models.ReferenceType.VOID_REVERSAL


def test_post_financial_event_borrowed_funding_classified_correctly(client, session):
    """When balance is zero, the entire outflow is classified as borrowed."""
    user, _wallet = _seed_user_with_wallet(client, session, "ledger7@example.com")

    empty_wallet = models.Wallet(
        owner_id=user.id,
        name="Empty credit card",
        wallet_type=models.WalletType.CREDIT,
        accounting_type=models.AccountingType.LIABILITY,
        initial_balance=0,
        current_balance=0,
        credit_limit=1_000_000,
        is_default=False,
    )
    session.add(empty_wallet)
    session.commit()
    session.refresh(empty_wallet)

    event = post_financial_event(
        session,
        owner_id=user.id,
        title="Borrowed spend",
        event_type=models.TransactionType.EXPENSE,
        date=user_timezone_today(),
        entity_category=models.ExpenseCategory.ELECTRONICS,
        wallet_legs=[
            PostWalletLeg(wallet_id=empty_wallet.id, amount=-200_000),
        ],
        entity_legs=[
            PostEntityLeg(
                label="Borrowed spend",
                amount=200_000,
                category=models.ExpenseCategory.ELECTRONICS,
            ),
        ],
    )

    session.expire_all()
    event_from_db = session.query(models.FinancialEvent).filter(
        models.FinancialEvent.id == event.id,
    ).first()
    leg = event_from_db.wallet_legs[0]
    assert leg.owned_spend_amount == 0  # nothing owned
    assert leg.borrowed_spend_amount == 200_000  # fully borrowed


# ---------------------------------------------------------------------------
# Expense Posting integration tests
# ---------------------------------------------------------------------------


def test_post_expense_event_uses_financial_event_ledger_seam(client, session):
    """Normal expense posting creates a correctly-shaped FinancialEvent via the
    ledger seam."""
    user, wallet = _seed_user_with_wallet(client, session, "ledger8@example.com")

    budget = models.Budget(
        owner_id=user.id,
        category=models.ExpenseCategory.GROCERIES,
        monthly_limit=500_000,
        budget_year=2026,
        budget_month=7,
    )
    session.add(budget)
    session.commit()
    session.refresh(budget)

    result = post_expense_event(
        session,
        user.id,
        title="Ledger seam integration",
        amount=50_000,
        category=models.ExpenseCategory.GROCERIES,
        expense_date=user_timezone_today(),
        description="integration test",
    )

    event = result.event
    assert event.event_type == models.TransactionType.EXPENSE
    assert event.status == models.FinancialEventStatus.POSTED
    assert event.title == "Ledger seam integration"
    assert event.is_session is False
    assert len(event.wallet_legs) == 1
    assert event.wallet_legs[0].wallet_id == wallet.id
    assert event.wallet_legs[0].amount == -50_000
    assert event.wallet_legs[0].owned_spend_amount is not None
    assert event.wallet_legs[0].borrowed_spend_amount is not None
    assert len(event.entity_legs) == 1
    assert event.entity_legs[0].amount == 50_000
    assert event.entity_legs[0].category == models.ExpenseCategory.GROCERIES
    assert event.entity_legs[0].budget_id is not None


def test_post_expense_event_preserves_budget_required_failure(client, session):
    """Budget-required failure still returns the structured error used by the
    Global Budget Interceptor."""
    user, _wallet = _seed_user_with_wallet(client, session, "ledger9@example.com")

    from fastapi import HTTPException

    try:
        post_expense_event(
            session,
            user.id,
            title="No budget",
            amount=10_000,
            category=models.ExpenseCategory.GROCERIES,
            expense_date=user_timezone_today(),
        )
        assert False, "Expected HTTPException"
    except HTTPException as exc:
        assert exc.status_code == 400
        assert exc.detail == "expenses.budget_required"


def test_post_expense_event_preserves_wallet_protection_behavior(client, session):
    """Wallet balance floors remain enforced through the seam."""
    user, _wallet = _seed_user_with_wallet(client, session, "ledger10@example.com")

    budget = models.Budget(
        owner_id=user.id,
        category=models.ExpenseCategory.ELECTRONICS,
        monthly_limit=5_000_000,
        budget_year=2026,
        budget_month=7,
    )
    session.add(budget)
    session.commit()
    session.refresh(budget)

    tiny_wallet = models.Wallet(
        owner_id=user.id,
        name="Tiny cash",
        wallet_type=models.WalletType.CASH,
        accounting_type=models.AccountingType.ASSET,
        initial_balance=5_000,
        current_balance=5_000,
        is_default=False,
    )
    session.add(tiny_wallet)
    session.commit()
    session.refresh(tiny_wallet)

    from fastapi import HTTPException

    try:
        post_expense_event(
            session,
            user.id,
            title="Too much",
            amount=10_000,
            category=models.ExpenseCategory.ELECTRONICS,
            expense_date=user_timezone_today(),
            wallet_allocations=[{"wallet_id": tiny_wallet.id, "amount": 10_000}],
        )
        assert False, "Expected HTTPException for insufficient funds"
    except HTTPException as exc:
        assert exc.status_code == 400


def test_route_creates_expense_through_ledger_seam(client, session):
    """End-to-end: a normal expense via POST /expenses produces correct ledger rows."""
    headers = create_user_and_token(
        client, "expregression", "expregression@example.com", "Password123!"
    )
    create_budget(client, headers, category="Transport", monthly_limit=500_000)

    res = client.post(
        "/expenses/",
        json={
            "title": "Regression test expense",
            "amount": 75_000,
            "category": "Transport",
            "description": "regression payload",
            "date": user_timezone_today().isoformat(),
        },
        headers=headers,
    )

    assert res.status_code == 201, res.text
    data = res.json()
    assert data["title"] == "Regression test expense"
    assert data["amount"] == 75_000
    assert data["category"] == "Transport"
    assert data["is_session"] is False
    assert data["wallet_id"] is not None

    session.expire_all()
    event = session.query(models.FinancialEvent).filter(
        models.FinancialEvent.id == data["id"],
    ).first()
    assert event is not None
    assert event.event_type == models.TransactionType.EXPENSE
    assert event.status == models.FinancialEventStatus.POSTED
    assert len(event.wallet_legs) == 1
    assert event.wallet_legs[0].amount == -75_000
    assert event.wallet_legs[0].owned_spend_amount is not None
    assert len(event.entity_legs) == 1
    assert event.entity_legs[0].amount == 75_000
    assert event.entity_legs[0].budget_id is not None


def test_expense_void_still_works_with_ledger_seam(client, session):
    """Voiding an expense still creates a proper reversal (unchanged path)."""
    headers = create_user_and_token(
        client, "expvoidregress", "expvoidregress@example.com", "Password123!"
    )
    create_budget(client, headers, category="Utilities", monthly_limit=500_000)

    created = client.post(
        "/expenses/",
        json={
            "title": "To be voided",
            "amount": 30_000,
            "category": "Utilities",
            "description": "will be voided",
            "date": user_timezone_today().isoformat(),
        },
        headers=headers,
    )
    assert created.status_code == 201, created.text
    expense_id = created.json()["id"]

    deleted = client.delete(f"/expenses/{expense_id}", headers=headers)
    assert deleted.status_code == 204

    session.expire_all()
    original = session.query(models.FinancialEvent).filter(
        models.FinancialEvent.id == expense_id,
    ).first()
    assert original is not None
    assert original.status == models.FinancialEventStatus.VOIDED
    assert original.void_reversal_event_id is not None

    reversal = session.query(models.FinancialEvent).filter(
        models.FinancialEvent.id == original.void_reversal_event_id,
    ).first()
    assert reversal is not None
    assert reversal.status == models.FinancialEventStatus.REVERSAL
    assert reversal.reverses_event_id == original.id
