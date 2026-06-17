from tests.helpers import create_user_and_token, user_timezone_today
from app import models


def _default_wallet_id(client, headers):
    response = client.get("/wallets", headers=headers)
    assert response.status_code == 200
    return response.json()[0]["id"]


def _create_transferred_debt(client, headers, wallet_id, amount=1_000_000):
    today = user_timezone_today().isoformat()
    response = client.post(
        "/debts",
        json={
            "debt_type": "OWING",
            "counterparty_name": "Bank loan",
            "initial_amount": amount,
            "currency": "UZS",
            "date": today,
            "is_money_transferred": True,
            "initial_wallet_id": wallet_id,
        },
        headers=headers,
    )
    assert response.status_code == 201, response.text
    return response.json()


def test_debt_creation_writes_initial_ledger_entry(client, session):
    headers = create_user_and_token(client, "debtledger1", "debtledger1@example.com", "Password123!")
    wallet_id = _default_wallet_id(client, headers)

    debt = _create_transferred_debt(client, headers, wallet_id)

    detail = client.get(f"/debts/{debt['id']}", headers=headers)
    assert detail.status_code == 200
    payload = detail.json()
    assert payload["remaining_amount"] == 1_000_000
    assert payload["ledger_entries"][0]["entry_type"] == "INITIAL"
    assert payload["ledger_entries"][0]["amount_delta"] == 1_000_000
    assert payload["ledger_entries"][0]["financial_event_id"] is not None

    entries = session.query(models.DebtLedgerEntry).filter_by(debt_id=debt["id"]).all()
    assert len(entries) == 1
    assert entries[0].entry_type == models.DebtLedgerEntryType.INITIAL


def test_debt_list_projects_negative_wallet_obligations_without_debt_rows(client, session):
    headers = create_user_and_token(client, "debtwalletobligation", "debtwalletobligation@example.com", "Password123!")
    user = session.query(models.User).filter_by(email="debtwalletobligation@example.com").first()
    assert user is not None

    credit = client.post(
        "/wallets",
        json={
            "name": "Credit Card",
            "wallet_type": "CREDIT",
            "accounting_type": "LIABILITY",
            "initial_balance": -500_000,
            "credit_limit": 2_000_000,
        },
        headers=headers,
    )
    assert credit.status_code == 201, credit.text
    overdraft = client.post(
        "/wallets",
        json={
            "name": "Overdraft Debit",
            "wallet_type": "DEBIT",
            "accounting_type": "ASSET",
            "initial_balance": -200_000,
            "has_overdraft": True,
            "overdraft_limit": 500_000,
        },
        headers=headers,
    )
    assert overdraft.status_code == 201, overdraft.text
    positive = client.post(
        "/wallets",
        json={
            "name": "Positive Debit",
            "wallet_type": "DEBIT",
            "initial_balance": 100_000,
        },
        headers=headers,
    )
    assert positive.status_code == 201, positive.text
    zero_credit = client.post(
        "/wallets",
        json={
            "name": "Zero Credit",
            "wallet_type": "CREDIT",
            "accounting_type": "LIABILITY",
            "initial_balance": 0,
            "credit_limit": 2_000_000,
        },
        headers=headers,
    )
    assert zero_credit.status_code == 201, zero_credit.text

    debt_count_before = session.query(models.Debt).filter_by(owner_id=user.id).count()

    response = client.get("/debts", headers=headers)
    assert response.status_code == 200, response.text
    payload = response.json()

    wallet_items = [item for item in payload["items"] if item["source_type"] == "WALLET"]
    assert payload["total"] == 2
    assert sorted((item["wallet_id"], item["remaining_amount"], item["wallet_type"]) for item in wallet_items) == [
        (credit.json()["id"], 500_000, "CREDIT"),
        (overdraft.json()["id"], 200_000, "DEBIT"),
    ]
    omitted_wallet_ids = {positive.json()["id"], zero_credit.json()["id"]}
    assert omitted_wallet_ids - {item["wallet_id"] for item in wallet_items} == omitted_wallet_ids
    assert all(item["available_actions"] == ["wallet_transfer_payoff"] for item in wallet_items)
    assert session.query(models.Debt).filter_by(owner_id=user.id).count() == debt_count_before

    projected_actions = client.get(f"/debts/{-credit.json()['id']}/actions", headers=headers)
    assert projected_actions.status_code == 404


def test_credit_wallet_obligation_payoff_uses_transfer_with_fee_not_debt_payment(client, session):
    headers = create_user_and_token(client, "creditpayoff", "creditpayoff@example.com", "Password123!")
    user = session.query(models.User).filter_by(email="creditpayoff@example.com").first()
    assert user is not None

    source = client.post(
        "/wallets",
        json={
            "name": "Salary Wallet",
            "wallet_type": "DEBIT",
            "initial_balance": 1_000_000,
        },
        headers=headers,
    )
    assert source.status_code == 201, source.text
    credit = client.post(
        "/wallets",
        json={
            "name": "Credit Card",
            "wallet_type": "CREDIT",
            "accounting_type": "LIABILITY",
            "initial_balance": -500_000,
            "credit_limit": 2_000_000,
        },
        headers=headers,
    )
    assert credit.status_code == 201, credit.text

    response = client.post(
        f"/debts/wallet-obligations/{credit.json()['id']}/payoff",
        json={
            "from_wallet_id": source.json()["id"],
            "amount": 200_000,
            "fee_amount": 5_000,
            "fee_wallet_id": source.json()["id"],
            "fee_note": "repayment fee",
            "date": user_timezone_today().isoformat(),
        },
        headers=headers,
    )

    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["to_wallet_id"] == credit.json()["id"]
    assert payload["fee_event_id"] is not None

    session.expire_all()
    source_wallet = session.query(models.Wallet).filter(models.Wallet.id == source.json()["id"]).first()
    credit_wallet = session.query(models.Wallet).filter(models.Wallet.id == credit.json()["id"]).first()
    assert source_wallet.current_balance == 795_000
    assert credit_wallet.current_balance == -300_000

    transfer_event = session.query(models.FinancialEvent).filter(models.FinancialEvent.id == payload["id"]).first()
    assert transfer_event.event_type == models.TransactionType.TRANSFER
    assert transfer_event.reference_type == models.ReferenceType.WALLET_OBLIGATION_PAYOFF
    assert transfer_event.description == "Credit card repayment: Credit Card"
    transfer_entities = session.query(models.EntityLedger).filter(models.EntityLedger.event_id == transfer_event.id).all()
    assert len(transfer_entities) == 1
    assert transfer_entities[0].category is None

    fee_event = session.query(models.FinancialEvent).filter(models.FinancialEvent.id == payload["fee_event_id"]).first()
    assert fee_event.event_type == models.TransactionType.EXPENSE
    assert fee_event.reference_type == models.ReferenceType.BANK_FEE
    fee_entity = session.query(models.EntityLedger).filter(models.EntityLedger.event_id == fee_event.id).first()
    assert fee_entity.category == models.ExpenseCategory.BANK_FEES_INTEREST
    assert session.query(models.Debt).filter_by(owner_id=user.id).count() == 0
    assert session.query(models.DebtTransaction).filter_by(owner_id=user.id).count() == 0
    assert session.query(models.DebtLedgerEntry).filter_by(owner_id=user.id).count() == 0


def test_overdraft_wallet_obligation_payoff_uses_transfer_not_expense(client, session):
    headers = create_user_and_token(client, "overdraftpayoff", "overdraftpayoff@example.com", "Password123!")
    user = session.query(models.User).filter_by(email="overdraftpayoff@example.com").first()
    assert user is not None

    source = client.post(
        "/wallets",
        json={
            "name": "Checking",
            "wallet_type": "DEBIT",
            "initial_balance": 1_000_000,
        },
        headers=headers,
    )
    assert source.status_code == 201, source.text
    overdraft = client.post(
        "/wallets",
        json={
            "name": "Overdraft Debit",
            "wallet_type": "DEBIT",
            "initial_balance": -200_000,
            "has_overdraft": True,
            "overdraft_limit": 500_000,
        },
        headers=headers,
    )
    assert overdraft.status_code == 201, overdraft.text

    response = client.post(
        f"/debts/wallet-obligations/{overdraft.json()['id']}/payoff",
        json={
            "from_wallet_id": source.json()["id"],
            "amount": 150_000,
            "date": user_timezone_today().isoformat(),
        },
        headers=headers,
    )

    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["fee_event_id"] is None

    session.expire_all()
    source_wallet = session.query(models.Wallet).filter(models.Wallet.id == source.json()["id"]).first()
    overdraft_wallet = session.query(models.Wallet).filter(models.Wallet.id == overdraft.json()["id"]).first()
    assert source_wallet.current_balance == 850_000
    assert overdraft_wallet.current_balance == -50_000

    transfer_event = session.query(models.FinancialEvent).filter(models.FinancialEvent.id == payload["id"]).first()
    assert transfer_event.event_type == models.TransactionType.TRANSFER
    assert transfer_event.reference_type == models.ReferenceType.WALLET_OBLIGATION_PAYOFF
    assert transfer_event.description == "Overdraft cover: Overdraft Debit"
    assert session.query(models.FinancialEvent).filter_by(owner_id=user.id, event_type=models.TransactionType.EXPENSE).count() == 0
    assert session.query(models.Debt).filter_by(owner_id=user.id).count() == 0
    assert session.query(models.DebtTransaction).filter_by(owner_id=user.id).count() == 0


def test_debt_charge_and_payment_reconcile_from_debt_ledger(client):
    headers = create_user_and_token(client, "debtledger2", "debtledger2@example.com", "Password123!")
    wallet_id = _default_wallet_id(client, headers)
    debt = _create_transferred_debt(client, headers, wallet_id)

    charge = client.post(
        f"/debts/{debt['id']}/add-charge",
        json={"amount": 200_000, "reason": "Interest"},
        headers=headers,
    )
    assert charge.status_code == 201, charge.text

    payment = client.post(
        "/debts/transactions",
        json={
            "debt_id": debt["id"],
            "amount": 300_000,
            "date": user_timezone_today().isoformat(),
            "wallet_id": wallet_id,
        },
        headers=headers,
    )
    assert payment.status_code == 201, payment.text

    detail = client.get(f"/debts/{debt['id']}", headers=headers)
    assert detail.status_code == 200
    payload = detail.json()
    assert payload["remaining_amount"] == 900_000
    assert payload["total_charges"] == 200_000
    deltas = sorted(entry["amount_delta"] for entry in payload["ledger_entries"])
    assert deltas == [-300_000, 200_000, 1_000_000]


def test_deleting_debt_payment_adds_reversal_ledger_entry(client):
    headers = create_user_and_token(client, "debtledger3", "debtledger3@example.com", "Password123!")
    wallet_id = _default_wallet_id(client, headers)
    debt = _create_transferred_debt(client, headers, wallet_id)
    assert client.post(
        f"/debts/{debt['id']}/add-charge",
        json={"amount": 200_000, "reason": "Interest"},
        headers=headers,
    ).status_code == 201
    payment = client.post(
        "/debts/transactions",
        json={
            "debt_id": debt["id"],
            "amount": 300_000,
            "date": user_timezone_today().isoformat(),
            "wallet_id": wallet_id,
        },
        headers=headers,
    )
    transaction_id = payment.json()["id"]

    deleted = client.delete(f"/debts/transactions/{transaction_id}", headers=headers)
    assert deleted.status_code == 204

    detail = client.get(f"/debts/{debt['id']}", headers=headers)
    assert detail.status_code == 200
    payload = detail.json()
    assert payload["remaining_amount"] == 1_200_000
    reversal = [entry for entry in payload["ledger_entries"] if entry["entry_type"] == "REVERSAL"]
    assert len(reversal) == 1
    assert reversal[0]["amount_delta"] == 300_000
    assert reversal[0]["reverses_entry_id"] is not None


def test_forgive_debt_closes_balance_through_ledger(client):
    headers = create_user_and_token(client, "debtledger4", "debtledger4@example.com", "Password123!")
    wallet_id = _default_wallet_id(client, headers)
    debt = _create_transferred_debt(client, headers, wallet_id)

    forgiven = client.post(f"/debts/{debt['id']}/forgive", headers=headers)
    assert forgiven.status_code == 200, forgiven.text
    payload = forgiven.json()
    assert payload["status"] == "FORGIVEN"
    assert payload["remaining_amount"] == 0

    detail = client.get(f"/debts/{debt['id']}", headers=headers)
    forgiveness = [entry for entry in detail.json()["ledger_entries"] if entry["entry_type"] == "FORGIVENESS"]
    assert len(forgiveness) == 1
    assert forgiveness[0]["amount_delta"] == -1_000_000
