"""Tests for Ticket 2: Enforce Wallet Epochs on Expected Inflow Receipts.

Verifies that Expected Inflow realization validates destination wallet epochs
before posting money, same-day receipts are accepted, multi-wallet validation
works, and rejected commands create no side effects.
"""

from datetime import date, datetime, timedelta, timezone

from app import models
from tests.helpers import (
    TEST_TIMEZONE,
    create_budget,
    create_user_and_token,
    user_timezone_today,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _create_income_source(client, headers, name="Salary Source"):
    """Create an active income source and return its id."""
    res = client.post(
        "/income/sources",
        json={"name": name},
        headers=headers,
    )
    assert res.status_code == 201, res.text
    return res.json()["id"]


def _create_earned_promise(client, headers, source_id, amount=100_000, due_date=None):
    """Create an EARNED Expected Inflow promise and return its id and schedule id."""
    if due_date is None:
        due_date = user_timezone_today()
    res = client.post(
        "/expected-inflows",
        json={
            "kind": "EARNED",
            "source_id": source_id,
            "amount": amount,
            "due_date": due_date.isoformat(),
            "title": "Test EARNED Promise",
        },
        headers=headers,
    )
    assert res.status_code == 201, f"Create promise failed: {res.json()}"
    data = res.json()
    schedule_id = data["schedules"][0]["id"] if data.get("schedules") else None
    return data["id"], schedule_id


def _get_wallet_by_name(session, owner_id, name):
    return (
        session.query(models.Wallet)
        .filter(models.Wallet.owner_id == owner_id, models.Wallet.name == name)
        .first()
    )


# ---------------------------------------------------------------------------
# Ticket 2: EARNED income receipt — pre-epoch rejection
# ---------------------------------------------------------------------------

def test_realize_earned_before_wallet_epoch_is_rejected(client, session):
    """Realizing EARNED income before the destination wallet's tracking
    start must be rejected with a structured wallet epoch error."""
    headers = create_user_and_token(
        client, "eiepoch1", "eiepoch1@example.com", "Password123!"
    )
    today = user_timezone_today()
    create_budget(
        client, headers,
        category="Groceries", monthly_limit=500_000,
        budget_year=today.year, budget_month=today.month,
    )
    source_id = _create_income_source(client, headers, "Salary")

    user = session.query(models.User).filter(models.User.email == "eiepoch1@example.com").first()

    # Give the wallet a tracking-start date AFTER today so today's date
    # is before the wallet's epoch.  The future-date gate checks
    # "received_date > today" and today == received_date passes it.
    wallet = (
        session.query(models.Wallet)
        .filter(models.Wallet.owner_id == user.id, models.Wallet.is_default)
        .first()
    )
    wallet_epoch = today + timedelta(days=1)
    wallet.created_at = datetime(wallet_epoch.year, wallet_epoch.month, wallet_epoch.day,
                                  tzinfo=timezone.utc)
    session.commit()

    promise_id, _ = _create_earned_promise(
        client, headers, source_id, amount=50_000, due_date=today
    )

    res = client.post(
        f"/expected-inflows/{promise_id}/realize",
        json={
            "actual_amount": 50_000,
            "received_date": today.isoformat(),
            "wallet_allocations": [{"wallet_id": wallet.id, "amount": 50_000}],
        },
        headers=headers,
    )
    assert res.status_code == 400, f"Expected 400, got {res.status_code}: {res.json()}"
    detail = res.json()["detail"]
    assert detail["code"] == "wallets.date_before_epoch", f"Got detail: {detail}"
    assert detail["wallet_name"] == wallet.name
    assert detail["requested_date"] == today.isoformat()
    assert detail["wallet_epoch"] == wallet_epoch.isoformat()


# ---------------------------------------------------------------------------
# Ticket 2: Same-day acceptance
# ---------------------------------------------------------------------------


def test_realize_earned_same_day_as_wallet_epoch_is_accepted(client, session):
    """Same-day receipt on the destination wallet's tracking start is accepted."""
    headers = create_user_and_token(
        client, "eiepoch2", "eiepoch2@example.com", "Password123!"
    )
    today = user_timezone_today()
    create_budget(
        client, headers,
        category="Groceries", monthly_limit=500_000,
        budget_year=today.year, budget_month=today.month,
    )
    source_id = _create_income_source(client, headers, "Freelance")

    user = session.query(models.User).filter(models.User.email == "eiepoch2@example.com").first()
    wallet = (
        session.query(models.Wallet)
        .filter(models.Wallet.owner_id == user.id, models.Wallet.is_default)
        .first()
    )
    # Set epoch to today so same-day is valid
    wallet.created_at = datetime(today.year, today.month, today.day, tzinfo=timezone.utc)
    session.commit()

    promise_id, _ = _create_earned_promise(
        client, headers, source_id, amount=30_000, due_date=today
    )

    res = client.post(
        f"/expected-inflows/{promise_id}/realize",
        json={
            "actual_amount": 30_000,
            "received_date": today.isoformat(),
            "wallet_allocations": [{"wallet_id": wallet.id, "amount": 30_000}],
        },
        headers=headers,
    )
    assert res.status_code in (200, 201), f"Expected 200/201, got {res.status_code}: {res.json()}"
    data = res.json()
    assert data["realization"]["actual_amount"] == 30_000


# ---------------------------------------------------------------------------
# Ticket 2: Multi-wallet validation
# ---------------------------------------------------------------------------


def test_multi_wallet_receipt_rejects_if_any_wallet_is_pre_epoch(client, session):
    """Multi-wallet receipts must validate every destination wallet and
    reject the whole command if any one wallet is invalid."""
    headers = create_user_and_token(
        client, "eiepoch3", "eiepoch3@example.com", "Password123!"
    )
    today = user_timezone_today()
    create_budget(
        client, headers,
        category="Groceries", monthly_limit=500_000,
        budget_year=today.year, budget_month=today.month,
    )
    source_id = _create_income_source(client, headers, "Consulting")

    user = session.query(models.User).filter(models.User.email == "eiepoch3@example.com").first()

    # Good wallet: epoch in the distant past
    good_wallet = (
        session.query(models.Wallet)
        .filter(models.Wallet.owner_id == user.id, models.Wallet.is_default)
        .first()
    )
    good_wallet.created_at = datetime(2020, 1, 1, tzinfo=timezone.utc)
    good_wallet.initial_balance = 5_000_000
    good_wallet.current_balance = 5_000_000

    # Bad wallet: epoch is tomorrow (today's date is before its tracking start)
    bad_wallet_epoch = today + timedelta(days=1)
    bad_wallet = models.Wallet(
        owner_id=user.id,
        name="Future Wallet",
        wallet_type=models.WalletType.CASH,
        accounting_type=models.AccountingType.ASSET,
        initial_balance=5_000_000,
        current_balance=5_000_000,
        created_at=datetime(bad_wallet_epoch.year, bad_wallet_epoch.month,
                            bad_wallet_epoch.day, tzinfo=timezone.utc),
    )
    session.add(bad_wallet)
    session.commit()

    promise_id, _ = _create_earned_promise(
        client, headers, source_id, amount=40_000, due_date=today
    )

    res = client.post(
        f"/expected-inflows/{promise_id}/realize",
        json={
            "actual_amount": 40_000,
            "received_date": today.isoformat(),
            "wallet_allocations": [
                {"wallet_id": good_wallet.id, "amount": 20_000},
                {"wallet_id": bad_wallet.id, "amount": 20_000},
            ],
        },
        headers=headers,
    )
    assert res.status_code == 400, (
        f"Expected 400 for multi-wallet with one pre-epoch, "
        f"got {res.status_code}: {res.json()}"
    )
    detail = res.json()["detail"]
    assert detail["code"] == "wallets.date_before_epoch", f"Got detail: {detail}"
    assert detail["wallet_name"] == bad_wallet.name


# ---------------------------------------------------------------------------
# Ticket 2: rejected commands create NO side effects
# ---------------------------------------------------------------------------


def test_rejected_earned_receipt_creates_no_side_effects(client, session):
    """A rejected EARNED receipt must create no FinancialEvent, WalletLedger,
    EntityLedger, realization, allocation, or wallet balance change."""
    headers = create_user_and_token(
        client, "eiepoch4", "eiepoch4@example.com", "Password123!"
    )
    today = user_timezone_today()
    create_budget(
        client, headers,
        category="Groceries", monthly_limit=500_000,
        budget_year=today.year, budget_month=today.month,
    )
    source_id = _create_income_source(client, headers, "Side Gig")

    user = session.query(models.User).filter(models.User.email == "eiepoch4@example.com").first()
    wallet = (
        session.query(models.Wallet)
        .filter(models.Wallet.owner_id == user.id, models.Wallet.is_default)
        .first()
    )
    wallet_balance_before = int(wallet.current_balance)
    wallet.created_at = datetime(
        (today + timedelta(days=1)).year,
        (today + timedelta(days=1)).month,
        (today + timedelta(days=1)).day,
        tzinfo=timezone.utc,
    )
    session.commit()

    event_count_before = (
        session.query(models.FinancialEvent)
        .filter(models.FinancialEvent.owner_id == user.id)
        .count()
    )
    ledger_count_before = (
        session.query(models.WalletLedger)
        .filter(models.WalletLedger.owner_id == user.id)
        .count()
    )

    promise_id, _ = _create_earned_promise(
        client, headers, source_id, amount=50_000, due_date=today
    )

    res = client.post(
        f"/expected-inflows/{promise_id}/realize",
        json={
            "actual_amount": 50_000,
            "received_date": today.isoformat(),
            "wallet_allocations": [{"wallet_id": wallet.id, "amount": 50_000}],
        },
        headers=headers,
    )
    assert res.status_code == 400

    # Verify no side effects
    session.expire_all()
    wallet_after = (
        session.query(models.Wallet)
        .filter(models.Wallet.id == wallet.id)
        .first()
    )
    assert int(wallet_after.current_balance) == wallet_balance_before, (
        f"Balance changed from {wallet_balance_before} to {wallet_after.current_balance}"
    )

    event_count_after = (
        session.query(models.FinancialEvent)
        .filter(models.FinancialEvent.owner_id == user.id)
        .count()
    )
    assert event_count_after == event_count_before, (
        f"Event count changed {event_count_before} → {event_count_after}"
    )

    ledger_count_after = (
        session.query(models.WalletLedger)
        .filter(models.WalletLedger.owner_id == user.id)
        .count()
    )
    assert ledger_count_after == ledger_count_before

    realization_count = (
        session.query(models.ExpectedInflowRealization)
        .filter(models.ExpectedInflowRealization.promise_id == promise_id)
        .count()
    )
    assert realization_count == 0, f"Expected 0 realizations, found {realization_count}"


# ---------------------------------------------------------------------------
# Ticket 2: Multi-wallet same-day acceptance
# ---------------------------------------------------------------------------


def test_multi_wallet_same_day_receipt_accepted(client, session):
    """Multi-wallet receipt with all wallets at or before receipt date is accepted."""
    headers = create_user_and_token(
        client, "eiepoch5", "eiepoch5@example.com", "Password123!"
    )
    today = user_timezone_today()
    create_budget(
        client, headers,
        category="Groceries", monthly_limit=500_000,
        budget_year=today.year, budget_month=today.month,
    )
    source_id = _create_income_source(client, headers, "Dividends")

    user = session.query(models.User).filter(models.User.email == "eiepoch5@example.com").first()

    wallet1 = (
        session.query(models.Wallet)
        .filter(models.Wallet.owner_id == user.id, models.Wallet.is_default)
        .first()
    )
    wallet1.created_at = datetime(2024, 6, 1, tzinfo=timezone.utc)
    wallet1.initial_balance = 3_000_000
    wallet1.current_balance = 3_000_000

    wallet2 = models.Wallet(
        owner_id=user.id,
        name="Savings Account",
        wallet_type=models.WalletType.CASH,
        accounting_type=models.AccountingType.ASSET,
        initial_balance=3_000_000,
        current_balance=3_000_000,
        created_at=datetime(2024, 6, 1, tzinfo=timezone.utc),
    )
    session.add(wallet2)
    session.commit()

    promise_id, _ = _create_earned_promise(
        client, headers, source_id, amount=30_000, due_date=today
    )

    res = client.post(
        f"/expected-inflows/{promise_id}/realize",
        json={
            "actual_amount": 30_000,
            "received_date": today.isoformat(),
            "wallet_allocations": [
                {"wallet_id": wallet1.id, "amount": 15_000},
                {"wallet_id": wallet2.id, "amount": 15_000},
            ],
        },
        headers=headers,
    )
    assert res.status_code in (200, 201), (
        f"Expected 200/201 for valid multi-wallet receipt, "
        f"got {res.status_code}: {res.json()}"
    )


# ---------------------------------------------------------------------------
# Ticket 2: explicit timezone headers
# ---------------------------------------------------------------------------


def test_explicit_timezone_header_accepted(client, session):
    """A valid current-date realization is accepted with explicit X-Timezone headers."""
    headers = create_user_and_token(
        client, "eiepoch6", "eiepoch6@example.com", "Password123!"
    )
    today = user_timezone_today()
    create_budget(
        client, headers,
        category="Groceries", monthly_limit=500_000,
        budget_year=today.year, budget_month=today.month,
    )
    source_id = _create_income_source(client, headers, "Teaching")

    user = session.query(models.User).filter(models.User.email == "eiepoch6@example.com").first()
    wallet = (
        session.query(models.Wallet)
        .filter(models.Wallet.owner_id == user.id, models.Wallet.is_default)
        .first()
    )
    wallet.created_at = datetime(2020, 1, 1, tzinfo=timezone.utc)
    session.commit()

    promise_id, _ = _create_earned_promise(
        client, headers, source_id, amount=10_000, due_date=today
    )

    assert headers.get("X-Timezone") == TEST_TIMEZONE

    res = client.post(
        f"/expected-inflows/{promise_id}/realize",
        json={
            "actual_amount": 10_000,
            "received_date": today.isoformat(),
            "wallet_allocations": [{"wallet_id": wallet.id, "amount": 10_000}],
        },
        headers=headers,
    )
    assert res.status_code in (200, 201), (
        f"Expected 200/201, got {res.status_code}: {res.json()}"
    )
