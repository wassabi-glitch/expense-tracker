"""Wallet projection verification tests (Ticket 8).

Prove that wallet.current_balance is a trustworthy projection from the
immutable WalletLedger entries — after create, void, reversal, and
corrected repost flows.
"""

from datetime import date, datetime, timezone

from app import models
from app.domains.ledger import (
    verify_all_wallet_projections,
    verify_wallet_projection,
    void_financial_event,
)
from app.domains.posting._posting_service import post_expense_event
from app.timezone import resolve_effective_timezone
from tests.helpers import (
    TEST_WALLET_EPOCH,
    create_budget,
    create_user_and_token,
    user_timezone_today,
)


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------


def _default_wallet(client, headers):
    response = client.get("/wallets", headers=headers)
    assert response.status_code == 200, response.text
    return response.json()[0]


def _create_wallet(session, user_id, name="Second Wallet", balance=1_000_000):
    wallet = models.Wallet(
        owner_id=user_id,
        name=name,
        wallet_type=models.WalletType.CASH,
        accounting_type=models.AccountingType.ASSET,
        initial_balance=balance,
        current_balance=balance,
        is_default=False,
        created_at=TEST_WALLET_EPOCH,
    )
    session.add(wallet)
    session.commit()
    session.refresh(wallet)
    return wallet


def _user(session, email):
    return session.query(models.User).filter(models.User.email == email).first()


# =========================================================================
# Normal posted money event → projection (checkbox 1)
# =========================================================================


def test_normal_expense_projection_is_valid(client, session):
    """After a normal expense post, the wallet balance matches its ledger
    projection (initial_balance + SUM(wallet_ledger.amount))."""
    headers = create_user_and_token(
        client, "proj1", "proj1@example.com", "Password123!"
    )
    create_budget(client, headers, category="Groceries", monthly_limit=500_000)
    wallet = _default_wallet(client, headers)
    user = _user(session, "proj1@example.com")

    # Post an expense.
    created = client.post(
        "/expenses/",
        json={
            "title": "Projection test",
            "amount": 30_000,
            "category": "Groceries",
            "date": user_timezone_today().isoformat(),
        },
        headers=headers,
    )
    assert created.status_code == 201, created.text

    session.expire_all()
    result = verify_wallet_projection(session, wallet_id=wallet["id"])
    assert result.is_valid, result.detail
    # Wallet started at 10M, expense 30k → 9_970_000
    assert result.current_balance == 10_000_000 - 30_000
    assert result.expected_balance == result.current_balance
    assert result.event_count == 1


def test_normal_income_projection_is_valid(client, session):
    """After a normal income post, the wallet balance matches its ledger
    projection."""
    headers = create_user_and_token(
        client, "proj2", "proj2@example.com", "Password123!"
    )
    source = client.post("/income/sources", json={"name": "Salary"}, headers=headers)
    assert source.status_code == 201, source.text
    source_id = source.json()["id"]
    wallet = _default_wallet(client, headers)

    created = client.post(
        "/income/entries",
        json={
            "amount": 500_000,
            "source_id": source_id,
            "date": user_timezone_today().isoformat(),
        },
        headers=headers,
    )
    assert created.status_code == 201, created.text
    created_wallet_id = created.json()["wallet_allocations"][0]["wallet_id"]

    session.expire_all()
    result = verify_wallet_projection(session, wallet_id=created_wallet_id)
    assert result.is_valid, result.detail
    assert result.current_balance == 10_000_000 + 500_000
    assert result.expected_balance == result.current_balance


# =========================================================================
# Void / reversal → projection (checkbox 2)
# =========================================================================


def test_expense_void_projection_is_valid(client, session):
    """After voiding a posted expense, the wallet balance returns to its
    pre-expense value and the projection stays valid."""
    headers = create_user_and_token(
        client, "proj3", "proj3@example.com", "Password123!"
    )
    create_budget(client, headers, category="Groceries", monthly_limit=500_000)
    wallet = _default_wallet(client, headers)

    # Snapshot before.
    session.expire_all()
    before = verify_wallet_projection(session, wallet_id=wallet["id"])
    assert before.is_valid, before.detail
    balance_before = before.current_balance

    created = client.post(
        "/expenses/",
        json={
            "title": "To void",
            "amount": 40_000,
            "category": "Groceries",
            "date": user_timezone_today().isoformat(),
        },
        headers=headers,
    )
    assert created.status_code == 201, created.text
    expense_id = created.json()["id"]

    session.expire_all()
    after_expense = verify_wallet_projection(session, wallet_id=wallet["id"])
    assert after_expense.is_valid, after_expense.detail
    assert after_expense.current_balance == balance_before - 40_000

    # Void the expense.
    deleted = client.delete(f"/expenses/{expense_id}", headers=headers)
    assert deleted.status_code == 204

    session.expire_all()
    after_void = verify_wallet_projection(session, wallet_id=wallet["id"])
    assert after_void.is_valid, after_void.detail
    # Balance must be restored — no double-application (checkbox 6).
    assert after_void.current_balance == balance_before, (
        f"Balance after void ({after_void.current_balance}) "
        f"should equal balance before expense ({balance_before}). "
        f"Double-application would give {balance_before - 40_000 - 40_000}."
    )


def test_income_delete_void_projection_is_valid(client, session):
    """Deleting posted income goes through void_and_reverse, and the wallet
    projection stays valid."""
    headers = create_user_and_token(
        client, "proj4", "proj4@example.com", "Password123!"
    )
    source = client.post("/income/sources", json={"name": "Freelance"}, headers=headers)
    assert source.status_code == 201, source.text
    source_id = source.json()["id"]
    wallet = _default_wallet(client, headers)

    session.expire_all()
    before = verify_wallet_projection(session, wallet_id=wallet["id"])
    assert before.is_valid, before.detail
    balance_before = before.current_balance

    created = client.post(
        "/income/entries",
        json={
            "amount": 200_000,
            "source_id": source_id,
            "date": user_timezone_today().isoformat(),
        },
        headers=headers,
    )
    assert created.status_code == 201, created.text
    income_id = created.json()["id"]

    # Delete (void+reverse) the income.
    deleted = client.delete(f"/income/entries/{income_id}", headers=headers)
    assert deleted.status_code == 204

    session.expire_all()
    after = verify_wallet_projection(session, wallet_id=wallet["id"])
    assert after.is_valid, after.detail
    assert after.current_balance == balance_before, (
        f"Balance after income delete should equal balance before income. "
        f"Got {after.current_balance}, expected {balance_before}."
    )


# =========================================================================
# Income corrected repost → projection (checkbox 3)
# =========================================================================


def test_income_amount_correction_projection_is_valid(client, session):
    """Changing an income amount triggers a correction repost. The wallet
    projection must stay valid and reflect only the corrected amount."""
    headers = create_user_and_token(
        client, "proj5", "proj5@example.com", "Password123!"
    )
    source = client.post("/income/sources", json={"name": "Salary"}, headers=headers)
    assert source.status_code == 201, source.text
    source_id = source.json()["id"]
    wallet = _default_wallet(client, headers)
    today = user_timezone_today()

    created = client.post(
        "/income/entries",
        json={
            "amount": 500_000,
            "source_id": source_id,
            "date": today.isoformat(),
        },
        headers=headers,
    )
    assert created.status_code == 201, created.text
    original_id = created.json()["id"]

    # Correct the amount.
    updated = client.put(
        f"/income/entries/{original_id}",
        json={
            "amount": 750_000,
            "source_id": source_id,
            "date": today.isoformat(),
        },
        headers=headers,
    )
    assert updated.status_code == 200, updated.text
    assert updated.json()["amount"] == 750_000

    session.expire_all()
    result = verify_wallet_projection(session, wallet_id=wallet["id"])
    assert result.is_valid, result.detail
    # Net effect: +500k (original) -500k (void) +750k (corrected) = +750k
    assert result.current_balance == 10_000_000 + 750_000, (
        f"Expected 10_750_000, got {result.current_balance}"
    )


def test_income_wallet_correction_no_stale_effects(client, session):
    """Changing an income wallet allocation leaves the old wallet with net
    zero effect and the new wallet with the full corrected amount (checkbox 7)."""
    email = "proj6@example.com"
    headers = create_user_and_token(client, "proj6", email, "Password123!")
    user = _user(session, email)
    default_wallet = (
        session.query(models.Wallet)
        .filter(models.Wallet.owner_id == user.id, models.Wallet.is_default)
        .first()
    )
    second_wallet = _create_wallet(session, user.id, "Side Wallet")
    source = client.post("/income/sources", json={"name": "Freelance"}, headers=headers)
    assert source.status_code == 201, source.text
    source_id = source.json()["id"]
    today = user_timezone_today()

    created = client.post(
        "/income/entries",
        json={
            "amount": 400_000,
            "source_id": source_id,
            "date": today.isoformat(),
            "wallet_id": default_wallet.id,
        },
        headers=headers,
    )
    assert created.status_code == 201, created.text
    original_id = created.json()["id"]

    # Switch wallet → correction repost.
    updated = client.put(
        f"/income/entries/{original_id}",
        json={
            "amount": 400_000,
            "source_id": source_id,
            "date": today.isoformat(),
            "wallet_id": second_wallet.id,
        },
        headers=headers,
    )
    assert updated.status_code == 200, updated.text

    session.expire_all()
    # Default wallet: +400k (original) -400k (void) = net 0 (no stale effect).
    dw_proj = verify_wallet_projection(session, wallet_id=default_wallet.id)
    assert dw_proj.is_valid, dw_proj.detail
    assert dw_proj.current_balance == 10_000_000, (
        f"Default wallet has stale effect: balance={dw_proj.current_balance}"
    )

    # Second wallet: +400k (corrected).
    sw_proj = verify_wallet_projection(session, wallet_id=second_wallet.id)
    assert sw_proj.is_valid, sw_proj.detail
    assert sw_proj.current_balance == 1_000_000 + 400_000, (
        f"Second wallet missing corrected amount: balance={sw_proj.current_balance}"
    )


# =========================================================================
# Multi-wallet projection (checkbox 4)
# =========================================================================


def test_multi_wallet_transfer_projections_are_valid(client, session):
    """A transfer between two wallets keeps both projections valid."""
    email = "proj7@example.com"
    headers = create_user_and_token(client, "proj7", email, "Password123!")
    user = _user(session, email)

    wallet_a = (
        session.query(models.Wallet)
        .filter(models.Wallet.owner_id == user.id, models.Wallet.is_default)
        .first()
    )
    wallet_b = _create_wallet(session, user.id, "Destination", 2_000_000)

    session.expire_all()
    a_before = verify_wallet_projection(session, wallet_id=wallet_a.id)
    b_before = verify_wallet_projection(session, wallet_id=wallet_b.id)
    assert a_before.is_valid and b_before.is_valid

    transfer = client.post(
        "/wallets/transfer",
        json={
            "from_wallet_id": wallet_a.id,
            "to_wallet_id": wallet_b.id,
            "amount": 300_000,
            "date": user_timezone_today().isoformat(),
        },
        headers=headers,
    )
    assert transfer.status_code == 200, transfer.text

    session.expire_all()
    a_after = verify_wallet_projection(session, wallet_id=wallet_a.id)
    b_after = verify_wallet_projection(session, wallet_id=wallet_b.id)
    assert a_after.is_valid, a_after.detail
    assert b_after.is_valid, b_after.detail
    assert a_after.current_balance == a_before.current_balance - 300_000
    assert b_after.current_balance == b_before.current_balance + 300_000


def test_multi_wallet_expense_allocation_projections_are_valid(client, session):
    """Multi-wallet expense allocations keep all touched wallets valid."""
    email = "proj8@example.com"
    headers = create_user_and_token(client, "proj8", email, "Password123!")
    create_budget(client, headers, category="Groceries", monthly_limit=500_000)
    user = _user(session, email)

    wallet_a = (
        session.query(models.Wallet)
        .filter(models.Wallet.owner_id == user.id, models.Wallet.is_default)
        .first()
    )
    wallet_b = _create_wallet(session, user.id, "Extra", 2_000_000)

    created = client.post(
        "/expenses/",
        json={
            "title": "Split expense",
            "amount": 150_000,
            "category": "Groceries",
            "date": user_timezone_today().isoformat(),
            "wallet_allocations": [
                {"wallet_id": wallet_a.id, "amount": 100_000},
                {"wallet_id": wallet_b.id, "amount": 50_000},
            ],
        },
        headers=headers,
    )
    assert created.status_code == 201, created.text

    session.expire_all()
    a_proj = verify_wallet_projection(session, wallet_id=wallet_a.id)
    b_proj = verify_wallet_projection(session, wallet_id=wallet_b.id)
    assert a_proj.is_valid, a_proj.detail
    assert b_proj.is_valid, b_proj.detail
    assert a_proj.current_balance == 10_000_000 - 100_000
    assert b_proj.current_balance == 2_000_000 - 50_000


# =========================================================================
# Opening snapshot / initial balance accounting (checkbox 5)
# =========================================================================


def test_projection_accounts_for_initial_balance(client, session):
    """The projection formula is initial_balance + SUM(wallet_ledger.amount).
    A wallet with no ledger entries should have current_balance == initial_balance."""
    email = "proj9@example.com"
    headers = create_user_and_token(client, "proj9", email, "Password123!")
    user = _user(session, email)

    # Create a fresh wallet with a non-zero initial_balance and no activity.
    fresh = _create_wallet(session, user.id, "Fresh Wallet", 5_000_000)

    session.expire_all()
    result = verify_wallet_projection(session, wallet_id=fresh.id)
    assert result.is_valid, result.detail
    assert result.current_balance == 5_000_000
    assert result.initial_balance == 5_000_000
    assert result.ledger_sum == 0
    assert result.event_count == 0
    assert result.expected_balance == 5_000_000


def test_projection_with_ledger_entries_accounts_for_initial_balance(client, session):
    """After activity, the projection still correctly includes initial_balance."""
    headers = create_user_and_token(
        client, "proj10", "proj10@example.com", "Password123!"
    )
    create_budget(client, headers, category="Groceries", monthly_limit=500_000)
    wallet = _default_wallet(client, headers)

    # The default wallet created by helpers has initial_balance = 10_000_000.
    session.expire_all()
    before = verify_wallet_projection(session, wallet_id=wallet["id"])
    assert before.is_valid, before.detail
    assert before.initial_balance == 10_000_000
    assert before.ledger_sum == 0
    assert before.current_balance == 10_000_000

    # Post two expenses.
    for _ in range(2):
        res = client.post(
            "/expenses/",
            json={
                "title": "Projection expense",
                "amount": 25_000,
                "category": "Groceries",
                "date": user_timezone_today().isoformat(),
            },
            headers=headers,
        )
        assert res.status_code == 201, res.text

    session.expire_all()
    after = verify_wallet_projection(session, wallet_id=wallet["id"])
    assert after.is_valid, after.detail
    assert after.initial_balance == 10_000_000
    assert after.ledger_sum == -50_000
    assert after.current_balance == 10_000_000 - 50_000
    assert after.expected_balance == after.current_balance


# =========================================================================
# verify_all_wallet_projections (all-at-once check)
# =========================================================================


def test_verify_all_wallets_returns_results_for_every_active_wallet(client, session):
    """verify_all_wallet_projections returns one result per active wallet."""
    email = "proj11@example.com"
    headers = create_user_and_token(client, "proj11", email, "Password123!")
    create_budget(client, headers, category="Groceries", monthly_limit=500_000)
    user = _user(session, email)
    _create_wallet(session, user.id, "Extra Wallet", 1_000_000)

    # Post an expense to create ledger activity.
    client.post(
        "/expenses/",
        json={
            "title": "Activity",
            "amount": 20_000,
            "category": "Groceries",
            "date": user_timezone_today().isoformat(),
        },
        headers=headers,
    )

    session.expire_all()
    results = verify_all_wallet_projections(session, owner_id=user.id)
    assert len(results) >= 2, f"Expected ≥2 wallets, got {len(results)}"
    assert all(p.is_valid for p in results), (
        [p.detail for p in results if not p.is_valid]
    )


# =========================================================================
# Debug information on failure (checkbox 8)
# =========================================================================


def test_projection_mismatch_produces_debug_info(client, session):
    """When the projection is invalid (e.g., balance manually changed),
    the WalletProjection dataclass exposes the delta and a human-readable
    detail message for debugging."""
    email = "proj12@example.com"
    headers = create_user_and_token(client, "proj12", email, "Password123!")
    user = _user(session, email)

    # Directly mutate the wallet balance to simulate a drift.
    wallet = (
        session.query(models.Wallet)
        .filter(models.Wallet.owner_id == user.id, models.Wallet.is_default)
        .first()
    )
    wallet.current_balance = 9_999_999  # off by 1
    session.commit()

    session.expire_all()
    result = verify_wallet_projection(session, wallet_id=wallet.id)
    assert not result.is_valid, "Projection should be invalid after manual mutation"
    assert result.delta == -1
    assert result.current_balance == 9_999_999
    assert result.expected_balance == 10_000_000
    assert "PROJECTION MISMATCH" in result.detail
    assert "delta=-1" in result.detail
    assert "Possible causes" in result.detail, (
        "Debug info should suggest possible causes"
    )


# =========================================================================
# No double-application on reversal (checkbox 6, direct seam)
# =========================================================================


def test_void_does_not_double_apply_wallet_effects(client, session):
    """Calling void_financial_event directly applies exactly one
    counter-balancing set of wallet legs — the wallet balance returns
    to its pre-event value, not lower."""
    headers = create_user_and_token(
        client, "proj13", "proj13@example.com", "Password123!"
    )
    create_budget(client, headers, category="Groceries", monthly_limit=500_000)
    user = _user(session, "proj13@example.com")

    wallet = (
        session.query(models.Wallet)
        .filter(models.Wallet.owner_id == user.id, models.Wallet.is_default)
        .first()
    )
    balance_before = wallet.current_balance

    result = post_expense_event(
        session,
        user.id,
        title="No-double-apply test",
        amount=30_000,
        category=models.ExpenseCategory.GROCERIES,
        expense_date=user_timezone_today(),
    )
    session.commit()

    session.expire_all()
    wallet = session.query(models.Wallet).filter(models.Wallet.id == wallet.id).first()
    assert wallet.current_balance == balance_before - 30_000

    user_tz = resolve_effective_timezone(x_timezone="Asia/Tashkent")
    void_financial_event(
        session,
        event=result.event,
        owner_id=user.id,
        user_tz=user_tz,
        void_reason="Test",
    )
    session.commit()

    session.expire_all()
    wallet = session.query(models.Wallet).filter(models.Wallet.id == wallet.id).first()
    assert wallet.current_balance == balance_before, (
        f"Double-application detected: balance={wallet.current_balance}, "
        f"expected={balance_before}. If void double-applied the net would "
        f"be {balance_before - 60_000}."
    )

    # Projection must be valid.
    proj = verify_wallet_projection(session, wallet_id=wallet.id)
    assert proj.is_valid, proj.detail


# =========================================================================
# WalletLeg level checks — no double or missing entries
# =========================================================================


def test_reversal_has_exactly_one_counter_balance_per_wallet_leg(client, session):
    """Each wallet leg on the original event produces exactly one negated
    leg on the reversal — no more, no less."""
    headers = create_user_and_token(
        client, "proj14", "proj14@example.com", "Password123!"
    )
    create_budget(client, headers, category="Groceries", monthly_limit=500_000)

    created = client.post(
        "/expenses/",
        json={
            "title": "Leg count test",
            "amount": 15_000,
            "category": "Groceries",
            "date": user_timezone_today().isoformat(),
        },
        headers=headers,
    )
    assert created.status_code == 201, created.text
    expense_id = created.json()["id"]

    session.expire_all()
    original = (
        session.query(models.FinancialEvent)
        .filter(models.FinancialEvent.id == expense_id)
        .first()
    )
    original_leg_count = len(original.wallet_legs)

    client.delete(f"/expenses/{expense_id}", headers=headers)

    session.expire_all()
    reversal = (
        session.query(models.FinancialEvent)
        .filter(models.FinancialEvent.id == original.void_reversal_event_id)
        .first()
    )
    assert reversal is not None
    assert len(reversal.wallet_legs) == original_leg_count, (
        f"Reversal has {len(reversal.wallet_legs)} wallet legs, "
        f"original had {original_leg_count}. Must be 1:1."
    )
    # Each reversal leg amount must be the negation of the corresponding original.
    for orig_leg in original.wallet_legs:
        matching = [
            rl for rl in reversal.wallet_legs
            if rl.wallet_id == orig_leg.wallet_id and rl.amount == -orig_leg.amount
        ]
        assert len(matching) == 1, (
            f"Original leg (wallet={orig_leg.wallet_id}, amount={orig_leg.amount}) "
            f"must have exactly one counter-balancing reversal leg. Found {len(matching)}."
        )
