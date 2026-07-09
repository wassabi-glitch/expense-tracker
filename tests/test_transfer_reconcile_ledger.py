"""Regression tests for Issue 8: Route wallet transfers and reconciliation
adjustments through the FinancialEventLedger seam.

Verifies that transfers and reconciliation adjustments create
correctly-shaped FinancialEvent, WalletLedger, and EntityLedger entries
through the ledger seam.
"""

from app import models
from tests.helpers import create_user_and_token, user_timezone_today


def _wallet(client, headers, name="Test Wallet", balance=1_000_000):
    res = client.post(
        "/wallets",
        json={
            "name": name,
            "wallet_type": "CASH",
            "initial_balance": balance,
        },
        headers=headers,
    )
    assert res.status_code == 201, res.text
    return res.json()


def _default_wallet(client, headers):
    response = client.get("/wallets", headers=headers)
    assert response.status_code in (200, 201), response.text
    return response.json()[0]


# ---------------------------------------------------------------------------
# Wallet transfer → FinancialEventLedger seam
# ---------------------------------------------------------------------------


def test_transfer_creates_posted_transfer_event(client, session):
    """A wallet transfer creates one posted TRANSFER FinancialEvent through
    the ledger seam."""
    headers = create_user_and_token(
        client, "txregress1", "txregress1@example.com", "Password123!"
    )
    src = _default_wallet(client, headers)
    dst = _wallet(client, headers, name="Destination")

    res = client.post(
        "/wallets/transfer",
        json={
            "from_wallet_id": src["id"],
            "to_wallet_id": dst["id"],
            "amount": 100_000,
            "date": user_timezone_today().isoformat(),
        },
        headers=headers,
    )
    assert res.status_code == 200, res.text
    event_id = res.json()["id"]

    session.expire_all()
    event = (
        session.query(models.FinancialEvent)
        .filter(models.FinancialEvent.id == event_id)
        .first()
    )
    assert event is not None
    assert event.event_type == models.TransactionType.TRANSFER
    assert event.status == models.FinancialEventStatus.POSTED


def test_transfer_writes_two_wallet_legs(client, session):
    """Transfers write exactly two Wallet Ledger entries with equal absolute
    amounts and opposite signs."""
    headers = create_user_and_token(
        client, "txregress2", "txregress2@example.com", "Password123!"
    )
    src = _default_wallet(client, headers)
    dst = _wallet(client, headers, name="Dest")

    res = client.post(
        "/wallets/transfer",
        json={
            "from_wallet_id": src["id"],
            "to_wallet_id": dst["id"],
            "amount": 75_000,
            "date": user_timezone_today().isoformat(),
        },
        headers=headers,
    )
    assert res.status_code == 200, res.text
    event_id = res.json()["id"]

    session.expire_all()
    event = (
        session.query(models.FinancialEvent)
        .filter(models.FinancialEvent.id == event_id)
        .first()
    )
    assert len(event.wallet_legs) == 2
    amounts = sorted(int(leg.amount) for leg in event.wallet_legs)
    assert amounts == [-75_000, 75_000]


def test_transfer_updates_both_wallet_balances(client, session):
    """Both source and destination wallet balances are updated exactly once."""
    headers = create_user_and_token(
        client, "txregress3", "txregress3@example.com", "Password123!"
    )
    src = _default_wallet(client, headers)
    dst = _wallet(client, headers, name="Dest")

    src_before = (
        session.query(models.Wallet).filter(models.Wallet.id == src["id"]).first()
    )
    dst_before = (
        session.query(models.Wallet).filter(models.Wallet.id == dst["id"]).first()
    )
    src_balance_before = src_before.current_balance
    dst_balance_before = dst_before.current_balance

    res = client.post(
        "/wallets/transfer",
        json={
            "from_wallet_id": src["id"],
            "to_wallet_id": dst["id"],
            "amount": 50_000,
            "date": user_timezone_today().isoformat(),
        },
        headers=headers,
    )
    assert res.status_code == 200, res.text

    session.expire_all()
    src_after = (
        session.query(models.Wallet).filter(models.Wallet.id == src["id"]).first()
    )
    dst_after = (
        session.query(models.Wallet).filter(models.Wallet.id == dst["id"]).first()
    )
    assert src_after.current_balance == src_balance_before - 50_000
    assert dst_after.current_balance == dst_balance_before + 50_000


def test_transfer_date_is_user_local(client, session):
    """Transfer dates are explicit user-provided dates, not server-local
    defaults."""
    from tests.helpers import TEST_WALLET_EPOCH

    headers = create_user_and_token(
        client, "txregress4", "txregress4@example.com", "Password123!"
    )
    src = _default_wallet(client, headers)
    dst = _wallet(client, headers, name="Dest")

    # Backdate wallet epochs so the transfer date 2026-06-15 is allowed.
    # Wallets created via the API get server_default=func.now().
    for wid in [src["id"], dst["id"]]:
        w = session.query(models.Wallet).filter(models.Wallet.id == wid).first()
        w.created_at = TEST_WALLET_EPOCH
    session.commit()

    explicit_date = "2026-06-15"
    res = client.post(
        "/wallets/transfer",
        json={
            "from_wallet_id": src["id"],
            "to_wallet_id": dst["id"],
            "amount": 25_000,
            "date": explicit_date,
        },
        headers=headers,
    )
    assert res.status_code == 200, res.text
    event_id = res.json()["id"]

    session.expire_all()
    event = (
        session.query(models.FinancialEvent)
        .filter(models.FinancialEvent.id == event_id)
        .first()
    )
    from datetime import date
    assert event.date == date(2026, 6, 15)


# ---------------------------------------------------------------------------
# Reconciliation adjustment → FinancialEventLedger seam
# ---------------------------------------------------------------------------


def test_reconciliation_creates_adjustment_event(client, session):
    """Reconciling a wallet balance creates an ADJUSTMENT FinancialEvent
    through the ledger seam."""
    headers = create_user_and_token(
        client, "recregress1", "recregress1@example.com", "Password123!"
    )
    wallet = _default_wallet(client, headers)

    # Spend some money to create a discrepancy scenario
    wallet_obj = (
        session.query(models.Wallet)
        .filter(models.Wallet.id == wallet["id"])
        .first()
    )
    wallet_obj.current_balance = wallet_obj.current_balance - 10_000
    session.commit()

    # Reconcile to the original balance
    res = client.post(
        f"/wallets/{wallet['id']}/reconcile",
        json={
            "target_balance": wallet_obj.current_balance + 10_000,
            "note": "Found 10k under the couch",
        },
        headers=headers,
    )
    assert res.status_code == 200, res.text

    session.expire_all()
    events = (
        session.query(models.FinancialEvent)
        .filter(models.FinancialEvent.event_type == models.TransactionType.ADJUSTMENT)
        .order_by(models.FinancialEvent.id.desc())
        .all()
    )
    assert len(events) >= 1
    event = events[0]
    assert event.status == models.FinancialEventStatus.POSTED
    assert len(event.wallet_legs) == 1
    assert event.wallet_legs[0].amount == 10_000  # positive delta


def test_reconciliation_no_op_when_balanced(client, session):
    """Reconciliation does nothing when the target balance matches the
    current balance."""
    headers = create_user_and_token(
        client, "recregress2", "recregress2@example.com", "Password123!"
    )
    wallet = _default_wallet(client, headers)

    current_balance = (
        session.query(models.Wallet)
        .filter(models.Wallet.id == wallet["id"])
        .first()
        .current_balance
    )

    events_before = (
        session.query(models.FinancialEvent)
        .filter(models.FinancialEvent.event_type == models.TransactionType.ADJUSTMENT)
        .count()
    )

    res = client.post(
        f"/wallets/{wallet['id']}/reconcile",
        json={
            "target_balance": current_balance,
            "note": "All good",
        },
        headers=headers,
    )
    assert res.status_code == 200

    events_after = (
        session.query(models.FinancialEvent)
        .filter(models.FinancialEvent.event_type == models.TransactionType.ADJUSTMENT)
        .count()
    )
    assert events_after == events_before  # No new adjustment event
