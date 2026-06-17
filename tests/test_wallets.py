from datetime import date

from app import models
from app.services.goal_funding_service import get_goal_funded_amount, get_goal_wallet_funded_amount
from tests.helpers import create_user_and_token


def _get_user(session, email: str) -> models.User:
    user = session.query(models.User).filter(models.User.email == email).first()
    assert user is not None
    return user


def _create_wallet(
    session,
    owner_id: int,
    name: str,
    *,
    initial_balance: int = 0,
    is_active: bool = True,
    is_default: bool = False,
) -> models.Wallet:
    wallet = models.Wallet(
        owner_id=owner_id,
        name=name,
        wallet_type=models.WalletType.DEBIT,
        accounting_type=models.AccountingType.ASSET,
        initial_balance=initial_balance,
        current_balance=initial_balance,
        is_active=is_active,
        is_default=is_default,
    )
    session.add(wallet)
    session.commit()
    session.refresh(wallet)
    return wallet


def _make_premium(client, headers):
    response = client.post("/users/me/toggle-premium", headers=headers)
    assert response.status_code == 200, response.text


def _create_goal_wallet(client, headers, *, name: str, initial_balance: int, wallet_type: str = "SAVINGS", can_fund_goals: bool = True, has_overdraft: bool = False, overdraft_limit: int = 0):
    response = client.post(
        "/wallets",
        json={
            "name": name,
            "wallet_type": wallet_type,
            "initial_balance": initial_balance,
            "can_fund_goals": can_fund_goals,
            "has_overdraft": has_overdraft,
            "overdraft_limit": overdraft_limit,
        },
        headers=headers,
    )
    assert response.status_code == 201, response.text
    return response.json()["id"]


def _create_goal_with_allocation(client, headers, wallet_id: int, *, amount: int):
    created = client.post(
        "/goals/",
        json={
            "title": "Protected Camera",
            "target_amount": amount,
            "intent": "RESERVE",
        },
        headers=headers,
    )
    assert created.status_code == 201, created.text
    goal_id = created.json()["id"]

    allocated = client.post(
        f"/goals/{goal_id}/allocations",
        json={"wallet_id": wallet_id, "amount": amount},
        headers=headers,
    )
    assert allocated.status_code == 200, allocated.text
    return goal_id


def test_list_wallets_excludes_archived_when_requested(client, session):
    headers = create_user_and_token(
        client,
        "walletuser1",
        "walletuser1@example.com",
        "Password123!",
    )
    user = _get_user(session, "walletuser1@example.com")
    _create_wallet(session, user.id, "Archived Wallet", is_active=False)

    res = client.get("/wallets?include_archived=false", headers=headers)

    assert res.status_code == 200
    names = {wallet["name"] for wallet in res.json()}
    assert "Default Wallet" in names
    assert "Archived Wallet" not in names


def test_archive_wallet_sets_is_active_false(client, session):
    headers = create_user_and_token(
        client,
        "walletuser2",
        "walletuser2@example.com",
        "Password123!",
    )
    user = _get_user(session, "walletuser2@example.com")
    wallet = _create_wallet(session, user.id, "Empty Wallet", initial_balance=0)

    res = client.delete(f"/wallets/{wallet.id}", headers=headers)

    assert res.status_code == 204
    session.refresh(wallet)
    assert wallet.is_active is False


def test_archive_wallet_requires_zero_balance(client, session):
    headers = create_user_and_token(
        client,
        "walletuser3",
        "walletuser3@example.com",
        "Password123!",
    )
    user = _get_user(session, "walletuser3@example.com")
    wallet = _create_wallet(session, user.id, "Non Zero Wallet", initial_balance=100)

    res = client.delete(f"/wallets/{wallet.id}", headers=headers)

    assert res.status_code == 400
    assert res.json()["detail"] == "wallets.archive_not_empty"
    session.refresh(wallet)
    assert wallet.is_active is True


def test_restore_wallet_via_patch(client, session):
    headers = create_user_and_token(
        client,
        "walletuser4",
        "walletuser4@example.com",
        "Password123!",
    )
    user = _get_user(session, "walletuser4@example.com")
    wallet = _create_wallet(session, user.id, "Archived Wallet", is_active=False)

    res = client.patch(f"/wallets/{wallet.id}", json={"is_active": True}, headers=headers)

    assert res.status_code == 200
    assert res.json()["is_active"] is True
    assert "status" not in res.json()
    session.refresh(wallet)
    assert wallet.is_active is True


def test_archived_wallet_cannot_transfer_funds(client, session):
    headers = create_user_and_token(
        client,
        "walletuser5",
        "walletuser5@example.com",
        "Password123!",
    )
    user = _get_user(session, "walletuser5@example.com")
    archived_wallet = _create_wallet(session, user.id, "Archived Source", initial_balance=500, is_active=False)
    active_wallet = _create_wallet(session, user.id, "Active Target", initial_balance=0)

    res = client.post(
        "/wallets/transfer",
        json={
            "from_wallet_id": archived_wallet.id,
            "to_wallet_id": active_wallet.id,
            "amount": 100,
            "note": "test transfer",
            "date": date.today().isoformat(),
        },
        headers=headers,
    )

    assert res.status_code == 400
    assert res.json()["detail"] == "wallets.is_archived"


def test_transfer_only_free_money_from_goal_funding_wallet(client, session):
    headers = create_user_and_token(
        client,
        "walletgoaltransferfree",
        "walletgoaltransferfree@example.com",
        "Password123!",
    )
    _make_premium(client, headers)
    source_id = _create_goal_wallet(client, headers, name="Savings Source", initial_balance=1_000_000)
    target_id = _create_goal_wallet(client, headers, name="Cash Target", initial_balance=0, wallet_type="CASH", can_fund_goals=False)
    goal_id = _create_goal_with_allocation(client, headers, source_id, amount=800_000)

    res = client.post(
        "/wallets/transfer",
        json={
            "from_wallet_id": source_id,
            "to_wallet_id": target_id,
            "amount": 200_000,
            "note": "free transfer",
            "date": date.today().isoformat(),
        },
        headers=headers,
    )

    assert res.status_code == 200, res.text
    session.expire_all()
    source = session.query(models.Wallet).filter(models.Wallet.id == source_id).first()
    target = session.query(models.Wallet).filter(models.Wallet.id == target_id).first()
    assert source.current_balance == 800_000
    assert target.current_balance == 200_000
    assert get_goal_wallet_funded_amount(session, source.owner_id, goal_id, source_id) == 800_000


def test_transfer_touching_goal_money_is_blocked_without_resolution(client, session):
    headers = create_user_and_token(
        client,
        "walletgoaltransferblock",
        "walletgoaltransferblock@example.com",
        "Password123!",
    )
    _make_premium(client, headers)
    source_id = _create_goal_wallet(client, headers, name="Savings Source", initial_balance=1_000_000)
    target_id = _create_goal_wallet(client, headers, name="Target", initial_balance=0, wallet_type="DEBIT", can_fund_goals=True)
    _create_goal_with_allocation(client, headers, source_id, amount=800_000)

    res = client.post(
        "/wallets/transfer",
        json={
            "from_wallet_id": source_id,
            "to_wallet_id": target_id,
            "amount": 300_000,
            "note": "blocked transfer",
            "date": date.today().isoformat(),
        },
        headers=headers,
    )

    assert res.status_code == 400
    detail = res.json()["detail"]
    assert detail["code"] == "wallets.goal_protection_conflict"
    assert detail["free_to_spend"] == 200_000
    assert detail["required_goal_resolution_amount"] == 100_000
    session.expire_all()
    source = session.query(models.Wallet).filter(models.Wallet.id == source_id).first()
    target = session.query(models.Wallet).filter(models.Wallet.id == target_id).first()
    assert source.current_balance == 1_000_000
    assert target.current_balance == 0


def test_transfer_can_move_touched_goal_allocation_to_destination(client, session):
    headers = create_user_and_token(
        client,
        "walletgoaltransfermove",
        "walletgoaltransfermove@example.com",
        "Password123!",
    )
    _make_premium(client, headers)
    source_id = _create_goal_wallet(client, headers, name="Old Debit", initial_balance=1_000_000)
    target_id = _create_goal_wallet(client, headers, name="New Debit", initial_balance=0, wallet_type="DEBIT", can_fund_goals=True)
    goal_id = _create_goal_with_allocation(client, headers, source_id, amount=800_000)

    res = client.post(
        "/wallets/transfer",
        json={
            "from_wallet_id": source_id,
            "to_wallet_id": target_id,
            "amount": 500_000,
            "note": "replace wallet",
            "date": date.today().isoformat(),
            "goal_resolution": "MOVE_TO_DESTINATION",
        },
        headers=headers,
    )

    assert res.status_code == 200, res.text
    session.expire_all()
    source = session.query(models.Wallet).filter(models.Wallet.id == source_id).first()
    target = session.query(models.Wallet).filter(models.Wallet.id == target_id).first()
    assert source.current_balance == 500_000
    assert target.current_balance == 500_000
    assert get_goal_funded_amount(session, source.owner_id, goal_id) == 800_000
    assert get_goal_wallet_funded_amount(session, source.owner_id, goal_id, source_id) == 500_000
    assert get_goal_wallet_funded_amount(session, source.owner_id, goal_id, target_id) == 300_000


def test_transfer_can_release_touched_goal_allocation(client, session):
    headers = create_user_and_token(
        client,
        "walletgoaltransferrelease",
        "walletgoaltransferrelease@example.com",
        "Password123!",
    )
    _make_premium(client, headers)
    source_id = _create_goal_wallet(client, headers, name="Savings Source", initial_balance=1_000_000)
    target_id = _create_goal_wallet(client, headers, name="Target", initial_balance=0, wallet_type="DEBIT", can_fund_goals=True)
    goal_id = _create_goal_with_allocation(client, headers, source_id, amount=800_000)

    res = client.post(
        "/wallets/transfer",
        json={
            "from_wallet_id": source_id,
            "to_wallet_id": target_id,
            "amount": 500_000,
            "note": "release goal money",
            "date": date.today().isoformat(),
            "goal_resolution": "RELEASE",
        },
        headers=headers,
    )

    assert res.status_code == 200, res.text
    session.expire_all()
    source = session.query(models.Wallet).filter(models.Wallet.id == source_id).first()
    assert source.current_balance == 500_000
    assert get_goal_funded_amount(session, source.owner_id, goal_id) == 500_000
    assert get_goal_wallet_funded_amount(session, source.owner_id, goal_id, source_id) == 500_000


def test_transfer_with_fee_records_linked_bank_fee(client, session):
    headers = create_user_and_token(
        client,
        "wallettransferfee",
        "wallettransferfee@example.com",
        "Password123!",
    )
    source_id = _create_goal_wallet(client, headers, name="Fee Source", initial_balance=1_000_000)
    target_id = _create_goal_wallet(client, headers, name="Fee Target", initial_balance=0, wallet_type="DEBIT", can_fund_goals=True)

    res = client.post(
        "/wallets/transfer",
        json={
            "from_wallet_id": source_id,
            "to_wallet_id": target_id,
            "amount": 100_000,
            "fee_amount": 5_000,
            "fee_wallet_id": source_id,
            "fee_note": "card transfer fee",
            "date": date.today().isoformat(),
        },
        headers=headers,
    )

    assert res.status_code == 200, res.text
    payload = res.json()
    assert payload["fee_event_id"] is not None
    session.expire_all()
    source = session.query(models.Wallet).filter(models.Wallet.id == source_id).first()
    target = session.query(models.Wallet).filter(models.Wallet.id == target_id).first()
    assert source.current_balance == 895_000
    assert target.current_balance == 100_000

    fee_event = session.query(models.FinancialEvent).filter(models.FinancialEvent.id == payload["fee_event_id"]).first()
    assert fee_event is not None
    assert fee_event.linked_event_id == payload["id"]
    assert fee_event.reference_type == models.ReferenceType.BANK_FEE
    assert fee_event.event_type == models.TransactionType.EXPENSE
    fee_entity = session.query(models.EntityLedger).filter(models.EntityLedger.event_id == fee_event.id).first()
    assert fee_entity is not None
    assert fee_entity.category == models.ExpenseCategory.BANK_FEES_INTEREST
    assert fee_entity.amount == 5_000


def test_transfer_fee_cannot_touch_protected_goal_money(client, session):
    headers = create_user_and_token(
        client,
        "wallettransferfeeprotected",
        "wallettransferfeeprotected@example.com",
        "Password123!",
    )
    _make_premium(client, headers)
    source_id = _create_goal_wallet(client, headers, name="Protected Fee Source", initial_balance=1_000_000)
    target_id = _create_goal_wallet(client, headers, name="Protected Fee Target", initial_balance=0, wallet_type="DEBIT", can_fund_goals=True)
    _create_goal_with_allocation(client, headers, source_id, amount=800_000)

    res = client.post(
        "/wallets/transfer",
        json={
            "from_wallet_id": source_id,
            "to_wallet_id": target_id,
            "amount": 200_000,
            "fee_amount": 10_000,
            "fee_wallet_id": source_id,
            "date": date.today().isoformat(),
        },
        headers=headers,
    )

    assert res.status_code == 400
    detail = res.json()["detail"]
    assert detail["code"] == "wallets.fee_goal_protection_conflict"
    assert detail["required_goal_resolution_amount"] == 10_000
    session.expire_all()
    source = session.query(models.Wallet).filter(models.Wallet.id == source_id).first()
    target = session.query(models.Wallet).filter(models.Wallet.id == target_id).first()
    assert source.current_balance == 1_000_000
    assert target.current_balance == 0


def test_archive_zero_balance_wallet_with_goal_allocations_is_blocked(client, session):
    headers = create_user_and_token(
        client,
        "walletgoalarchive",
        "walletgoalarchive@example.com",
        "Password123!",
    )
    _make_premium(client, headers)
    wallet_id = _create_goal_wallet(client, headers, name="Broken Wallet", initial_balance=100_000)
    _create_goal_with_allocation(client, headers, wallet_id, amount=100_000)

    wallet = session.query(models.Wallet).filter(models.Wallet.id == wallet_id).first()
    wallet.current_balance = 0
    session.commit()

    res = client.delete(f"/wallets/{wallet_id}", headers=headers)

    assert res.status_code == 400
    detail = res.json()["detail"]
    assert detail["code"] == "wallets.archive_has_goal_allocations"
    assert detail["protected_for_goals"] == 100_000
    session.refresh(wallet)
    assert wallet.is_active is True


def test_credit_repayment_from_protected_wallet_is_blocked(client, session):
    headers = create_user_and_token(
        client,
        "walletgoalcredit",
        "walletgoalcredit@example.com",
        "Password123!",
    )
    _make_premium(client, headers)
    source_id = _create_goal_wallet(client, headers, name="Debit Source", initial_balance=1_000_000)
    credit = client.post(
        "/wallets",
        json={
            "name": "Credit Card",
            "wallet_type": "CREDIT",
            "accounting_type": "LIABILITY",
            "initial_balance": -500_000,
            "credit_limit": 1_000_000,
        },
        headers=headers,
    )
    assert credit.status_code == 201, credit.text
    credit_id = credit.json()["id"]
    _create_goal_with_allocation(client, headers, source_id, amount=800_000)

    res = client.post(
        "/wallets/transfer",
        json={
            "from_wallet_id": source_id,
            "to_wallet_id": credit_id,
            "amount": 500_000,
            "note": "credit repayment",
            "date": date.today().isoformat(),
        },
        headers=headers,
    )

    assert res.status_code == 400
    assert res.json()["detail"]["code"] == "wallets.goal_protection_conflict"


def test_overdraft_transfer_must_move_goal_allocation_off_negative_wallet(client, session):
    headers = create_user_and_token(
        client,
        "walletgoaloverdraft",
        "walletgoaloverdraft@example.com",
        "Password123!",
    )
    _make_premium(client, headers)
    source_id = _create_goal_wallet(
        client,
        headers,
        name="Overdraft Debit",
        wallet_type="DEBIT",
        initial_balance=3_000_000,
        can_fund_goals=True,
        has_overdraft=True,
        overdraft_limit=10_000_000,
    )
    target_id = _create_goal_wallet(client, headers, name="New Savings", initial_balance=0)
    goal_id = _create_goal_with_allocation(client, headers, source_id, amount=3_000_000)

    blocked = client.post(
        "/wallets/transfer",
        json={
            "from_wallet_id": source_id,
            "to_wallet_id": target_id,
            "amount": 10_000_000,
            "note": "overdraft without resolution",
            "date": date.today().isoformat(),
        },
        headers=headers,
    )
    assert blocked.status_code == 400
    assert blocked.json()["detail"]["required_goal_resolution_amount"] == 3_000_000

    moved = client.post(
        "/wallets/transfer",
        json={
            "from_wallet_id": source_id,
            "to_wallet_id": target_id,
            "amount": 10_000_000,
            "note": "overdraft with moved funding",
            "date": date.today().isoformat(),
            "goal_resolution": "MOVE_TO_DESTINATION",
        },
        headers=headers,
    )
    assert moved.status_code == 200, moved.text

    session.expire_all()
    source = session.query(models.Wallet).filter(models.Wallet.id == source_id).first()
    target = session.query(models.Wallet).filter(models.Wallet.id == target_id).first()
    assert source.current_balance == -7_000_000
    assert target.current_balance == 10_000_000
    assert get_goal_wallet_funded_amount(session, source.owner_id, goal_id, source_id) == 0
    assert get_goal_wallet_funded_amount(session, source.owner_id, goal_id, target_id) == 3_000_000


def test_wallet_transactions_endpoint_filters_direction_and_posted_events(client, session):
    headers = create_user_and_token(
        client,
        "wallettransactions",
        "wallettransactions@example.com",
        "Password123!",
    )
    user = _get_user(session, "wallettransactions@example.com")
    source = _create_wallet(session, user.id, "Cash Source", initial_balance=1_000)
    target = _create_wallet(session, user.id, "Humo Target", initial_balance=0)

    transfer = client.post(
        "/wallets/transfer",
        json={
            "from_wallet_id": source.id,
            "to_wallet_id": target.id,
            "amount": 250,
            "note": "test transfer",
            "date": date(2026, 1, 2).isoformat(),
        },
        headers=headers,
    )
    assert transfer.status_code == 200, transfer.text
    transfer_event_id = transfer.json()["id"]

    voided_event = models.FinancialEvent(
        owner_id=user.id,
        title="Voided Expense",
        event_type=models.TransactionType.EXPENSE,
        status=models.FinancialEventStatus.VOIDED,
        date=date(2026, 1, 3),
    )
    session.add(voided_event)
    session.flush()
    session.add(
        models.WalletLedger(
            owner_id=user.id,
            event_id=voided_event.id,
            wallet_id=source.id,
            amount=-50,
        )
    )
    session.commit()

    expected_title = "Cash Source \u2192 Humo Target"
    transfer_event = session.query(models.FinancialEvent).filter(models.FinancialEvent.id == transfer_event_id).first()
    assert transfer_event.title == expected_title

    all_res = client.get(f"/wallets/{source.id}/transactions", headers=headers)
    assert all_res.status_code == 200, all_res.text
    all_payload = all_res.json()
    assert all_payload["total"] == 1
    assert all_payload["items"][0]["title"] == expected_title
    assert all_payload["items"][0]["amount"] == -250
    assert all_payload["items"][0]["event_type"] == "TRANSFER"
    assert all_payload["items"][0]["date"] == "2026-01-02"

    in_res = client.get(f"/wallets/{source.id}/transactions?direction=in", headers=headers)
    assert in_res.status_code == 200
    assert in_res.json()["total"] == 0

    out_res = client.get(f"/wallets/{source.id}/transactions?direction=out", headers=headers)
    assert out_res.status_code == 200
    assert out_res.json()["total"] == 1

    target_in_res = client.get(f"/wallets/{target.id}/transactions?direction=in", headers=headers)
    assert target_in_res.status_code == 200
    target_payload = target_in_res.json()
    assert target_payload["total"] == 1
    assert target_payload["items"][0]["amount"] == 250


def test_wallet_transactions_endpoint_requires_wallet_ownership(client, session):
    owner_headers = create_user_and_token(
        client,
        "wallettransactionsowner",
        "wallettransactionsowner@example.com",
        "Password123!",
    )
    other_headers = create_user_and_token(
        client,
        "wallettransactionsother",
        "wallettransactionsother@example.com",
        "Password123!",
    )
    owner = _get_user(session, "wallettransactionsowner@example.com")
    wallet = _create_wallet(session, owner.id, "Private Wallet", initial_balance=0)

    owner_res = client.get(f"/wallets/{wallet.id}/transactions", headers=owner_headers)
    assert owner_res.status_code == 200

    other_res = client.get(f"/wallets/{wallet.id}/transactions", headers=other_headers)
    assert other_res.status_code == 404
