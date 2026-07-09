"""Regression tests for Issue 7: Route earned income and expected inflow
receipt posting through the FinancialEventLedger seam.

Verifies that recording income creates correctly-shaped FinancialEvent,
WalletLedger, and EntityLedger entries through the ledger seam.
"""

from app import models
from tests.helpers import create_user_and_token, user_timezone_today


def _default_wallet(client, headers):
    response = client.get("/wallets", headers=headers)
    assert response.status_code == 200, response.text
    return response.json()[0]


# ---------------------------------------------------------------------------
# Income posting → FinancialEventLedger seam
# ---------------------------------------------------------------------------


def test_create_income_creates_posted_event(client, session):
    """Creating an income entry creates a posted INCOME FinancialEvent
    through the ledger seam."""
    headers = create_user_and_token(
        client, "incregress1", "incregress1@example.com", "Password123!"
    )
    wallet = _default_wallet(client, headers)

    source = client.post(
        "/income/sources",
        json={"name": "Salary"},
        headers=headers,
    )
    assert source.status_code == 201, source.text
    source_id = source.json()["id"]

    entry = client.post(
        "/income/entries",
        json={
            "amount": 500_000,
            "source_id": source_id,
            "wallet_id": wallet["id"],
            "date": user_timezone_today().isoformat(),
        },
        headers=headers,
    )
    assert entry.status_code == 201, entry.text
    event_id = entry.json()["id"]

    session.expire_all()
    event = (
        session.query(models.FinancialEvent)
        .filter(models.FinancialEvent.id == event_id)
        .first()
    )
    assert event is not None
    assert event.event_type == models.TransactionType.INCOME
    assert event.status == models.FinancialEventStatus.POSTED


def test_create_income_writes_positive_wallet_ledger(client, session):
    """Income Wallet Ledger entries have positive amounts and increase
    wallet balance."""
    headers = create_user_and_token(
        client, "incregress2", "incregress2@example.com", "Password123!"
    )
    wallet = _default_wallet(client, headers)

    source = client.post("/income/sources", json={"name": "Freelance"}, headers=headers)
    assert source.status_code == 201, source.text
    source_id = source.json()["id"]

    wallet_before = (
        session.query(models.Wallet)
        .filter(models.Wallet.id == wallet["id"])
        .first()
    )
    balance_before = wallet_before.current_balance

    entry = client.post(
        "/income/entries",
        json={
            "amount": 300_000,
            "source_id": source_id,
            "wallet_id": wallet["id"],
            "date": user_timezone_today().isoformat(),
        },
        headers=headers,
    )
    assert entry.status_code == 201, entry.text
    event_id = entry.json()["id"]

    session.expire_all()
    event = (
        session.query(models.FinancialEvent)
        .filter(models.FinancialEvent.id == event_id)
        .first()
    )
    assert len(event.wallet_legs) == 1
    leg = event.wallet_legs[0]
    assert leg.wallet_id == wallet["id"]
    assert leg.amount == 300_000  # positive = inflow

    refreshed_wallet = (
        session.query(models.Wallet)
        .filter(models.Wallet.id == wallet["id"])
        .first()
    )
    assert refreshed_wallet.current_balance == balance_before + 300_000


def test_create_income_preserves_source_link(client, session):
    """Income Entity Ledger entries preserve the income_source_id link."""
    headers = create_user_and_token(
        client, "incregress3", "incregress3@example.com", "Password123!"
    )
    wallet = _default_wallet(client, headers)

    source = client.post(
        "/income/sources",
        json={"name": "Dividends"},
        headers=headers,
    )
    assert source.status_code == 201, source.text
    source_id = source.json()["id"]

    entry = client.post(
        "/income/entries",
        json={
            "amount": 100_000,
            "source_id": source_id,
            "wallet_id": wallet["id"],
            "date": user_timezone_today().isoformat(),
        },
        headers=headers,
    )
    assert entry.status_code == 201, entry.text
    event_id = entry.json()["id"]

    session.expire_all()
    event = (
        session.query(models.FinancialEvent)
        .filter(models.FinancialEvent.id == event_id)
        .first()
    )
    assert len(event.entity_legs) == 1
    leg = event.entity_legs[0]
    assert leg.income_source_id == source_id
    assert int(leg.amount) == 100_000


def test_create_income_supports_multi_wallet(client, session):
    """Income can be allocated across multiple wallets, each with its own
    positive Wallet Leg."""
    headers = create_user_and_token(
        client, "incregress4", "incregress4@example.com", "Password123!"
    )
    wallet1 = _default_wallet(client, headers)

    wallet2_res = client.post(
        "/wallets",
        json={"name": "Savings", "wallet_type": "SAVINGS", "initial_balance": 100_000},
        headers=headers,
    )
    assert wallet2_res.status_code == 201, wallet2_res.text
    wallet2 = wallet2_res.json()

    source = client.post("/income/sources", json={"name": "Bonus"}, headers=headers)
    assert source.status_code == 201, source.text
    source_id = source.json()["id"]

    entry = client.post(
        "/income/entries",
        json={
            "amount": 400_000,
            "source_id": source_id,
            "wallet_allocations": [
                {"wallet_id": wallet1["id"], "amount": 250_000},
                {"wallet_id": wallet2["id"], "amount": 150_000},
            ],
            "date": user_timezone_today().isoformat(),
        },
        headers=headers,
    )
    assert entry.status_code == 201, entry.text
    event_id = entry.json()["id"]

    session.expire_all()
    event = (
        session.query(models.FinancialEvent)
        .filter(models.FinancialEvent.id == event_id)
        .first()
    )
    assert len(event.wallet_legs) == 2
    wallet_ids = {leg.wallet_id for leg in event.wallet_legs}
    assert wallet1["id"] in wallet_ids
    assert wallet2["id"] in wallet_ids
    total_inflow = sum(int(leg.amount) for leg in event.wallet_legs)
    assert total_inflow == 400_000


def test_create_income_rejects_wallet_allocation_mismatch(client, session):
    """Wallet allocation total must match the income amount."""
    headers = create_user_and_token(
        client, "incregress5", "incregress5@example.com", "Password123!"
    )
    wallet = _default_wallet(client, headers)

    source = client.post("/income/sources", json={"name": "Gift"}, headers=headers)
    assert source.status_code == 201, source.text
    source_id = source.json()["id"]

    blocked = client.post(
        "/income/entries",
        json={
            "amount": 100_000,
            "source_id": source_id,
            "wallet_allocations": [
                {"wallet_id": wallet["id"], "amount": 50_000},
            ],
            "date": user_timezone_today().isoformat(),
        },
        headers=headers,
    )
    assert blocked.status_code == 400
    assert "mismatch" in blocked.json()["detail"].lower()


def test_create_income_date_is_explicit(client, session):
    """Income dates are explicit user-provided dates, not server defaults."""
    headers = create_user_and_token(
        client, "incregress6", "incregress6@example.com", "Password123!"
    )
    wallet = _default_wallet(client, headers)

    source = client.post("/income/sources", json={"name": "Rent"}, headers=headers)
    assert source.status_code == 201, source.text
    source_id = source.json()["id"]

    explicit_date = "2026-07-01"
    entry = client.post(
        "/income/entries",
        json={
            "amount": 200_000,
            "source_id": source_id,
            "wallet_id": wallet["id"],
            "date": explicit_date,
        },
        headers=headers,
    )
    assert entry.status_code == 201, entry.text
    event_id = entry.json()["id"]

    session.expire_all()
    event = (
        session.query(models.FinancialEvent)
        .filter(models.FinancialEvent.id == event_id)
        .first()
    )
    from datetime import date
    assert event.date == date(2026, 7, 1)
