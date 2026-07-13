"""Tests for Ticket 2: Wallet epoch boundary enforcement.

Verifies that money movement cannot be dated before the relevant wallet's
creation date, same-day activity is allowed, and the rule is per-wallet.
"""

from datetime import date, datetime, timezone

from app import models
from app.domains.ledger import (
    WalletEpochError,
    validate_wallet_epochs,
)
from app.services.expense_posting_service import post_expense_event
from tests.helpers import (
    create_budget,
    create_user_and_token,
    user_timezone_today,
)


# ---------------------------------------------------------------------------
# Direct seam — validate_wallet_epochs
# ---------------------------------------------------------------------------


def test_same_day_activity_on_wallet_creation_date_is_allowed(client, session):
    """Ticket 2: Same-day activity on the wallet creation date is allowed."""
    headers = create_user_and_token(
        client, "epochsame1", "epochsame1@example.com", "Password123!"
    )
    today = user_timezone_today()
    create_budget(
        client, headers,
        category="Groceries", monthly_limit=500_000,
        budget_year=today.year, budget_month=today.month,
    )
    user = session.query(models.User).filter(models.User.email == "epochsame1@example.com").first()
    wallet = (
        session.query(models.Wallet)
        .filter(models.Wallet.owner_id == user.id, models.Wallet.is_default)
        .first()
    )

    # Use today as the epoch — same-day must be allowed
    wallet.created_at = datetime.now(timezone.utc)
    session.commit()

    # Same-day posting must succeed at the seam level
    validate_wallet_epochs(
        session,
        wallet_ids={wallet.id},
        event_date=today,
    )  # No exception expected

    # Also verify through the posting service
    result = post_expense_event(
        session,
        user.id,
        title="Same day expense",
        amount=5_000,
        category=models.ExpenseCategory.GROCERIES,
        expense_date=today,
    )
    assert result.event is not None


def test_pre_epoch_date_is_rejected(client, session):
    """Ticket 2: Money movement dated before the wallet epoch is rejected."""
    create_user_and_token(
        client, "epochreject1", "epochreject1@example.com", "Password123!"
    )
    user = session.query(models.User).filter(models.User.email == "epochreject1@example.com").first()
    wallet = (
        session.query(models.Wallet)
        .filter(models.Wallet.owner_id == user.id, models.Wallet.is_default)
        .first()
    )

    wallet.created_at = datetime(2025, 6, 15, 0, 0, 0, tzinfo=timezone.utc)
    session.commit()

    # Day before epoch must be rejected
    try:
        validate_wallet_epochs(
            session,
            wallet_ids={wallet.id},
            event_date=date(2025, 6, 14),
        )
        assert False, "Pre-epoch date should have been rejected"
    except WalletEpochError as exc:
        detail = exc.detail
        assert detail["code"] == "wallets.date_before_epoch"
        assert detail["wallet_id"] == wallet.id
        assert "before wallet" in detail["message"].lower()
        assert detail["requested_date"] == "2025-06-14"


def test_user_facing_error_explains_epoch_boundary(client, session):
    """Ticket 2: User-facing errors explain that the requested date is
    before the wallet's tracking start."""
    create_user_and_token(
        client, "epochexplain", "epochexplain@example.com", "Password123!"
    )
    user = session.query(models.User).filter(models.User.email == "epochexplain@example.com").first()
    wallet = (
        session.query(models.Wallet)
        .filter(models.Wallet.owner_id == user.id, models.Wallet.is_default)
        .first()
    )

    wallet.created_at = datetime(2024, 3, 1, 0, 0, 0, tzinfo=timezone.utc)
    session.commit()

    try:
        validate_wallet_epochs(
            session,
            wallet_ids={wallet.id},
            event_date=date(2024, 2, 28),
        )
        assert False
    except WalletEpochError as exc:
        detail = exc.detail
        assert detail["wallet_name"] == wallet.name
        assert detail["wallet_epoch"] == "2024-03-01"
        assert detail["requested_date"] == "2024-02-28"
        assert "same-day activity is allowed" in detail["message"].lower()


def test_epoch_rule_is_per_wallet_not_global(client, session):
    """Ticket 2: The wallet epoch rule is per wallet, not global per user.
    A newer wallet does not restrict an older wallet."""
    create_user_and_token(
        client, "epochperwallet", "epochperwallet@example.com", "Password123!"
    )
    user = session.query(models.User).filter(models.User.email == "epochperwallet@example.com").first()

    # Old wallet (epoch: 2020)
    old_wallet = (
        session.query(models.Wallet)
        .filter(models.Wallet.owner_id == user.id, models.Wallet.is_default)
        .first()
    )
    old_wallet.created_at = datetime(2020, 1, 1, tzinfo=timezone.utc)

    # New wallet (epoch: yesterday)
    from datetime import timedelta
    new_wallet = models.Wallet(
        owner_id=user.id,
        name="New Wallet",
        wallet_type=models.WalletType.CASH,
        accounting_type=models.AccountingType.ASSET,
        initial_balance=1_000_000,
        current_balance=1_000_000,
        created_at=datetime.now(timezone.utc) - timedelta(days=1),
    )
    session.add(new_wallet)
    session.commit()

    # Old wallet: date far in the past but after its epoch — allowed
    validate_wallet_epochs(
        session,
        wallet_ids={old_wallet.id},
        event_date=date(2022, 6, 1),
    )  # No exception

    # New wallet: same date is before its epoch — rejected
    try:
        validate_wallet_epochs(
            session,
            wallet_ids={new_wallet.id},
            event_date=date(2022, 6, 1),
        )
        assert False, "New wallet should reject date before its own epoch"
    except WalletEpochError:
        pass

    # Old wallet is not affected by the new wallet's restriction
    validate_wallet_epochs(
        session,
        wallet_ids={old_wallet.id},
        event_date=date(2022, 6, 1),
    )  # Still allowed


def test_multi_wallet_money_movement_validates_every_touched_wallet(client, session):
    """Ticket 2: Multi-wallet money movements validate every touched wallet."""
    headers = create_user_and_token(
        client, "epochmultiw", "epochmultiw@example.com", "Password123!"
    )
    create_budget(client, headers, category="Groceries", monthly_limit=500_000)
    user = session.query(models.User).filter(models.User.email == "epochmultiw@example.com").first()

    old_wallet = (
        session.query(models.Wallet)
        .filter(models.Wallet.owner_id == user.id, models.Wallet.is_default)
        .first()
    )
    old_wallet.created_at = datetime(2020, 1, 1, tzinfo=timezone.utc)

    new_wallet = models.Wallet(
        owner_id=user.id,
        name="Recent Wallet",
        wallet_type=models.WalletType.CASH,
        accounting_type=models.AccountingType.ASSET,
        initial_balance=1_000_000,
        current_balance=1_000_000,
        created_at=datetime(2025, 6, 1, tzinfo=timezone.utc),
    )
    session.add(new_wallet)
    session.commit()

    # Validate both wallets: new wallet blocks the date
    try:
        validate_wallet_epochs(
            session,
            wallet_ids={old_wallet.id, new_wallet.id},
            event_date=date(2024, 1, 1),
        )
        assert False, "Should reject because new_wallet epoch is 2025-06-01"
    except WalletEpochError as exc:
        assert exc.detail["wallet_id"] == new_wallet.id

    # Same date but only old wallet — allowed
    validate_wallet_epochs(
        session,
        wallet_ids={old_wallet.id},
        event_date=date(2024, 1, 1),
    )  # OK


def test_cash_and_credit_wallets_follow_same_epoch_principle(client, session):
    """Ticket 2: Cash wallets and credit wallets follow the same epoch
    principle."""
    create_user_and_token(
        client, "epochcredit", "epochcredit@example.com", "Password123!"
    )
    user = session.query(models.User).filter(models.User.email == "epochcredit@example.com").first()

    credit_wallet = models.Wallet(
        owner_id=user.id,
        name="Credit Card",
        wallet_type=models.WalletType.CREDIT,
        accounting_type=models.AccountingType.LIABILITY,
        initial_balance=0,
        current_balance=0,
        credit_limit=5_000_000,
        created_at=datetime(2025, 3, 1, tzinfo=timezone.utc),
    )
    session.add(credit_wallet)
    session.commit()

    # Same-day on epoch: allowed
    validate_wallet_epochs(
        session,
        wallet_ids={credit_wallet.id},
        event_date=date(2025, 3, 1),
    )  # No exception

    # Before epoch: rejected (same rule as cash)
    try:
        validate_wallet_epochs(
            session,
            wallet_ids={credit_wallet.id},
            event_date=date(2025, 2, 28),
        )
        assert False
    except WalletEpochError:
        pass


def test_transfer_validates_both_source_and_destination_wallet_epochs(client, session):
    """Ticket 2: Transfers validate both source and destination wallet epochs."""
    headers = create_user_and_token(
        client, "epochtransfer", "epochtransfer@example.com", "Password123!"
    )
    user = session.query(models.User).filter(models.User.email == "epochtransfer@example.com").first()

    source = (
        session.query(models.Wallet)
        .filter(models.Wallet.owner_id == user.id, models.Wallet.is_default)
        .first()
    )
    source.created_at = datetime(2020, 1, 1, tzinfo=timezone.utc)

    dest = models.Wallet(
        owner_id=user.id,
        name="Destination",
        wallet_type=models.WalletType.CASH,
        accounting_type=models.AccountingType.ASSET,
        initial_balance=0,
        current_balance=0,
        created_at=datetime(2025, 1, 1, tzinfo=timezone.utc),
    )
    session.add(dest)
    session.commit()

    # Date valid for source but before destination epoch
    blocked = client.post(
        "/wallets/transfer",
        json={
            "from_wallet_id": source.id,
            "to_wallet_id": dest.id,
            "amount": 100_000,
            "note": "test",
            "date": date(2024, 6, 1).isoformat(),
        },
        headers=headers,
    )
    assert blocked.status_code == 400
    detail = blocked.json()["detail"]
    assert detail["code"] == "wallets.date_before_epoch"
    assert detail["wallet_id"] == dest.id


def test_reconciliation_adjustment_rejected_before_target_wallet_epoch(client, session):
    """Ticket 2: Reconciliation adjustments cannot be dated before the
    target wallet epoch.  Tested through the WalletService seam since the
    route always uses today's date."""
    from app.services.wallet_service import WalletService

    create_user_and_token(
        client, "epochrecon", "epochrecon@example.com", "Password123!"
    )
    user = session.query(models.User).filter(models.User.email == "epochrecon@example.com").first()
    wallet = (
        session.query(models.Wallet)
        .filter(models.Wallet.owner_id == user.id, models.Wallet.is_default)
        .first()
    )
    wallet.created_at = datetime(2025, 1, 1, tzinfo=timezone.utc)
    session.commit()

    # Reconciliation before epoch must be rejected via the service seam
    try:
        WalletService.reconcile_balance(
            db=session,
            owner_id=user.id,
            wallet_id=wallet.id,
            target_balance=9_500_000,  # Different from current to force delta
            reconciliation_date=date(2024, 12, 31),
        )
        assert False, "Pre-epoch reconciliation should be rejected"
    except WalletEpochError as exc:
        assert exc.detail["code"] == "wallets.date_before_epoch"


def test_expense_route_rejects_pre_epoch_date_with_user_friendly_error(client, session):
    """Ticket 2: Creating an expense before the wallet epoch returns a
    structured, user-friendly error.

    Uses a wallet with a creation date within the current month so the
    expense date passes the normal-logging boundary (Ticket 3) but still
    fails the per-wallet epoch check (Ticket 2)."""
    from datetime import timedelta
    from tests.helpers import user_timezone_today

    headers = create_user_and_token(
        client, "epochroute", "epochroute@example.com", "Password123!"
    )
    today = user_timezone_today()
    # Use yesterday as the expense date (must be within current month)
    expense_date = today - timedelta(days=1)
    if expense_date.month != today.month:
        expense_date = today  # near month boundary, use today instead

    create_budget(
        client, headers, category="Groceries", monthly_limit=500_000,
        budget_year=today.year, budget_month=today.month,
    )
    user = session.query(models.User).filter(models.User.email == "epochroute@example.com").first()
    wallet = (
        session.query(models.Wallet)
        .filter(models.Wallet.owner_id == user.id, models.Wallet.is_default)
        .first()
    )
    # Set wallet epoch to today so expense_date (yesterday) is pre-epoch
    wallet.created_at = datetime(today.year, today.month, today.day, tzinfo=timezone.utc)
    session.commit()

    blocked = client.post(
        "/expenses/",
        json={
            "title": "Pre-epoch expense",
            "amount": 10_000,
            "category": "Groceries",
            "date": expense_date.isoformat(),
        },
        headers=headers,
    )
    assert blocked.status_code == 400, blocked.text
    detail = blocked.json()["detail"]
    assert detail["code"] == "wallets.date_before_epoch"
    assert detail["wallet_name"] == wallet.name


def test_income_route_rejects_pre_epoch_date(client, session):
    """Ticket 2: Creating income before the wallet epoch is rejected.

    Uses a wallet with tomorrow's date as epoch, so today's date passes
    the current-month validation but fails epoch validation.
    """
    from datetime import timedelta

    headers = create_user_and_token(
        client, "epochincome2", "epochincome2@example.com", "Password123!"
    )
    user = session.query(models.User).filter(models.User.email == "epochincome2@example.com").first()
    wallet = (
        session.query(models.Wallet)
        .filter(models.Wallet.owner_id == user.id, models.Wallet.is_default)
        .first()
    )
    # Set wallet epoch far enough in the future that a recent past date
    # is before the epoch.  Use the wallet's creation date minus 1 day
    # as the event date, but ensure that date is not also in the future
    # or a closed period.
    # Strategy: set the wallet's epoch to 2 days from now, then use an
    # event date that is 1 day from now (still before epoch, and same-month
    # so current-month validation passes).
    future_epoch = datetime.now(timezone.utc) + timedelta(days=2)
    wallet.created_at = future_epoch
    wallet_epoch = future_epoch.date()
    session.commit()

    # Verify the seam-level validation rejects the pre-epoch date.
    # Route-level testing is covered by test_income_entry_create_rejects_pre_epoch
    # which uses explicit dates.  This test validates the epoch seam itself.
    from app.domains.ledger import WalletEpochError, validate_wallet_epochs

    event_date = wallet_epoch - timedelta(days=1)
    try:
        validate_wallet_epochs(session, wallet_ids={wallet.id}, event_date=event_date)
        assert False, "Pre-epoch date should have been rejected"
    except WalletEpochError as exc:
        assert exc.detail["code"] == "wallets.date_before_epoch"
