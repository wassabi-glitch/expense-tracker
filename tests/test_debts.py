from datetime import timedelta

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
            "expected_return_date": today,
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


def test_debt_response_derives_lifecycle_and_time_status_from_balance_and_due_date(client):
    headers = create_user_and_token(client, "debtstate1", "debtstate1@example.com", "Password123!")
    wallet_id = _default_wallet_id(client, headers)
    yesterday = (user_timezone_today() - timedelta(days=1)).isoformat()

    debt = _create_transferred_debt(client, headers, wallet_id, amount=100_000)
    updated_due = client.patch(
        f"/debts/{debt['id']}",
        json={"date": yesterday, "expected_return_date": yesterday},
        headers=headers,
    )
    assert updated_due.status_code == 200, updated_due.text
    assert updated_due.json()["lifecycle_status"] == "OPEN"
    assert updated_due.json()["time_status"] == "OVERDUE"

    payment = client.post(
        f"/debts/{debt['id']}/payments",
        json={
            "amount": 100_000,
            "date": user_timezone_today().isoformat(),
            "wallet_allocations": [{"wallet_id": wallet_id, "amount": 100_000}],
        },
        headers=headers,
    )
    assert payment.status_code == 201, payment.text

    closed = client.get(f"/debts/{debt['id']}", headers=headers)
    assert closed.status_code == 200, closed.text
    payload = closed.json()
    assert payload["remaining_amount"] == 0
    assert payload["lifecycle_status"] == "CLOSED"
    assert payload["time_status"] is None


def test_debt_archive_is_separate_from_lifecycle_and_hidden_by_default(client):
    headers = create_user_and_token(client, "debtarchive1", "debtarchive1@example.com", "Password123!")
    wallet_id = _default_wallet_id(client, headers)
    debt = _create_transferred_debt(client, headers, wallet_id, amount=100_000)

    archived = client.post(f"/debts/{debt['id']}/archive", headers=headers)
    assert archived.status_code == 200, archived.text
    archived_payload = archived.json()
    assert archived_payload["is_archived"] is True
    assert archived_payload["archived_at"] is not None
    assert archived_payload["lifecycle_status"] == "OPEN"
    assert archived_payload["remaining_amount"] == 100_000

    ordinary_list = client.get("/debts", headers=headers)
    assert ordinary_list.status_code == 200, ordinary_list.text
    assert all(item["id"] != debt["id"] for item in ordinary_list.json()["items"])

    archived_list = client.get("/debts?archived=true", headers=headers)
    assert archived_list.status_code == 200, archived_list.text
    archived_items = archived_list.json()["items"]
    assert [item["id"] for item in archived_items] == [debt["id"]]

    restored = client.post(f"/debts/{debt['id']}/restore", headers=headers)
    assert restored.status_code == 200, restored.text
    restored_payload = restored.json()
    assert restored_payload["is_archived"] is False
    assert restored_payload["archived_at"] is None
    assert restored_payload["lifecycle_status"] == "OPEN"

    restored_list = client.get("/debts", headers=headers)
    assert any(item["id"] == debt["id"] for item in restored_list.json()["items"])


def test_closed_debt_can_be_archived_and_restored_as_closed(client):
    headers = create_user_and_token(client, "debtarchiveclosed", "debtarchiveclosed@example.com", "Password123!")
    wallet_id = _default_wallet_id(client, headers)
    debt = _create_transferred_debt(client, headers, wallet_id, amount=100_000)

    payment = client.post(
        f"/debts/{debt['id']}/payments",
        json={
            "amount": 100_000,
            "date": user_timezone_today().isoformat(),
            "wallet_allocations": [{"wallet_id": wallet_id, "amount": 100_000}],
        },
        headers=headers,
    )
    assert payment.status_code == 201, payment.text

    archived = client.post(f"/debts/{debt['id']}/archive", headers=headers)
    assert archived.status_code == 200, archived.text
    assert archived.json()["is_archived"] is True
    assert archived.json()["lifecycle_status"] == "CLOSED"
    assert archived.json()["time_status"] is None

    restored = client.post(f"/debts/{debt['id']}/restore", headers=headers)
    assert restored.status_code == 200, restored.text
    assert restored.json()["is_archived"] is False
    assert restored.json()["lifecycle_status"] == "CLOSED"
    assert restored.json()["time_status"] is None


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
    assert payload["total_paid"] == 300_000
    deltas = sorted(entry["amount_delta"] for entry in payload["ledger_entries"])
    assert deltas == [-300_000, 200_000, 1_000_000]


def test_debt_charge_reversal_nets_total_charges(client):
    headers = create_user_and_token(client, "debtledgerchargeback", "debtledgerchargeback@example.com", "Password123!")
    wallet_id = _default_wallet_id(client, headers)
    debt = _create_transferred_debt(client, headers, wallet_id)

    charge = client.post(
        f"/debts/{debt['id']}/add-charge",
        json={"amount": 200_000, "reason": "Interest posted by mistake"},
        headers=headers,
    )
    assert charge.status_code == 201, charge.text

    detail = client.get(f"/debts/{debt['id']}", headers=headers)
    assert detail.status_code == 200, detail.text
    charge_entry = next(entry for entry in detail.json()["ledger_entries"] if entry["entry_type"] == "CHARGE")

    reversed_response = client.post(
        f"/debts/{debt['id']}/ledger/{charge_entry['id']}/reverse",
        json={"note": "Charge reversed"},
        headers=headers,
    )
    assert reversed_response.status_code == 200, reversed_response.text
    payload = reversed_response.json()
    assert payload["remaining_amount"] == 1_000_000
    assert payload["total_charges"] == 0
    assert payload["total_paid"] == 0

    listed = client.get("/debts", headers=headers)
    assert listed.status_code == 200, listed.text
    listed_debt = next(item for item in listed.json()["items"] if item["id"] == debt["id"])
    assert listed_debt["total_charges"] == 0
    assert listed_debt["total_paid"] == 0


def test_component_aware_forgiveness_can_target_charges_without_touching_principal(client):
    headers = create_user_and_token(client, "debtforgivecharges", "debtforgivecharges@example.com", "Password123!")
    wallet_id = _default_wallet_id(client, headers)
    debt = _create_transferred_debt(client, headers, wallet_id)

    charge = client.post(
        f"/debts/{debt['id']}/add-charge",
        json={"amount": 200_000, "reason": "Late fee"},
        headers=headers,
    )
    assert charge.status_code == 201, charge.text

    forgiven = client.post(
        f"/debts/{debt['id']}/forgiveness",
        json={"amount": 150_000, "component": "CHARGES", "note": "Fee waived"},
        headers=headers,
    )
    assert forgiven.status_code == 200, forgiven.text
    payload = forgiven.json()
    assert payload["remaining_principal_amount"] == 1_000_000
    assert payload["remaining_charge_amount"] == 50_000
    assert payload["remaining_amount"] == 1_050_000
    assert payload["total_paid"] == 0

    detail = client.get(f"/debts/{debt['id']}", headers=headers).json()
    forgiveness = next(entry for entry in detail["ledger_entries"] if entry["entry_type"] == "FORGIVENESS")
    assert forgiveness["principal_delta"] == 0
    assert forgiveness["charge_delta"] == -150_000


def test_component_aware_principal_forgiveness_leaves_charges_open(client):
    headers = create_user_and_token(client, "debtforgiveprincipal", "debtforgiveprincipal@example.com", "Password123!")
    wallet_id = _default_wallet_id(client, headers)
    debt = _create_transferred_debt(client, headers, wallet_id)

    charge = client.post(
        f"/debts/{debt['id']}/add-charge",
        json={"amount": 200_000, "reason": "Interest"},
        headers=headers,
    )
    assert charge.status_code == 201, charge.text

    forgiven = client.post(
        f"/debts/{debt['id']}/forgiveness",
        json={"amount": 300_000, "component": "PRINCIPAL", "note": "Original debt reduced"},
        headers=headers,
    )
    assert forgiven.status_code == 200, forgiven.text
    payload = forgiven.json()
    assert payload["remaining_principal_amount"] == 700_000
    assert payload["remaining_charge_amount"] == 200_000
    assert payload["remaining_amount"] == 900_000
    assert payload["total_paid"] == 0


def test_partial_forgiveness_requires_component_intent(client):
    headers = create_user_and_token(client, "debtforgiveneedsintent", "debtforgiveneedsintent@example.com", "Password123!")
    wallet_id = _default_wallet_id(client, headers)
    debt = _create_transferred_debt(client, headers, wallet_id)

    response = client.post(
        f"/debts/{debt['id']}/forgiveness",
        json={"amount": 100_000, "note": "No component chosen"},
        headers=headers,
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "debts.forgiveness.component_required"


def test_component_aware_balance_correction_can_target_charges(client):
    headers = create_user_and_token(client, "debtadjustcharges", "debtadjustcharges@example.com", "Password123!")
    wallet_id = _default_wallet_id(client, headers)
    debt = _create_transferred_debt(client, headers, wallet_id)

    charge = client.post(
        f"/debts/{debt['id']}/add-charge",
        json={"amount": 200_000, "reason": "Fee"},
        headers=headers,
    )
    assert charge.status_code == 201, charge.text

    adjusted = client.post(
        f"/debts/{debt['id']}/balance-adjustments",
        json={"component": "CHARGES", "confirmed_charge_balance": 80_000, "note": "Fee corrected"},
        headers=headers,
    )
    assert adjusted.status_code == 200, adjusted.text
    payload = adjusted.json()
    assert payload["remaining_principal_amount"] == 1_000_000
    assert payload["remaining_charge_amount"] == 80_000
    assert payload["remaining_amount"] == 1_080_000
    assert payload["total_paid"] == 0

    detail = client.get(f"/debts/{debt['id']}", headers=headers).json()
    adjustment = next(entry for entry in detail["ledger_entries"] if entry["entry_type"] == "ADJUSTMENT")
    assert adjustment["principal_delta"] == 0
    assert adjustment["charge_delta"] == -120_000


def test_downward_balance_correction_does_not_count_as_paid(client):
    headers = create_user_and_token(client, "debtledgeradjust", "debtledgeradjust@example.com", "Password123!")
    wallet_id = _default_wallet_id(client, headers)
    debt = _create_transferred_debt(client, headers, wallet_id)

    adjusted = client.post(
        f"/debts/{debt['id']}/balance-adjustments",
        json={"confirmed_balance": 800_000, "note": "Statement correction"},
        headers=headers,
    )
    assert adjusted.status_code == 200, adjusted.text
    payload = adjusted.json()
    assert payload["remaining_amount"] == 800_000
    assert payload["total_paid"] == 0

    detail = client.get(f"/debts/{debt['id']}", headers=headers)
    assert detail.status_code == 200, detail.text
    assert detail.json()["total_paid"] == 0


def test_reversal_blocks_older_entry_when_newer_same_debt_action_exists(client):
    headers = create_user_and_token(client, "debtreverselifo", "debtreverselifo@example.com", "Password123!")
    wallet_id = _default_wallet_id(client, headers)
    debt = _create_transferred_debt(client, headers, wallet_id)

    charge = client.post(
        f"/debts/{debt['id']}/add-charge",
        json={"amount": 200_000, "reason": "Fee"},
        headers=headers,
    )
    assert charge.status_code == 201, charge.text
    payment = client.post(
        f"/debts/{debt['id']}/payments",
        json={
            "amount": 100_000,
            "allocation_mode": "PRINCIPAL_FIRST",
            "date": user_timezone_today().isoformat(),
            "wallet_allocations": [{"wallet_id": wallet_id, "amount": 100_000}],
        },
        headers=headers,
    )
    assert payment.status_code == 201, payment.text

    detail = client.get(f"/debts/{debt['id']}", headers=headers).json()
    charge_entry = next(entry for entry in detail["ledger_entries"] if entry["entry_type"] == "CHARGE")
    blocked = client.post(
        f"/debts/{debt['id']}/ledger/{charge_entry['id']}/reverse",
        json={"note": "Trying old reversal"},
        headers=headers,
    )
    assert blocked.status_code == 400
    assert blocked.json()["detail"] == "debts.policy.reverse_latest_first"


def test_reversal_lifo_is_scoped_to_each_debt(client):
    headers = create_user_and_token(client, "debtreversescope", "debtreversescope@example.com", "Password123!")
    wallet_id = _default_wallet_id(client, headers)
    first = _create_transferred_debt(client, headers, wallet_id, amount=500_000)
    second = _create_transferred_debt(client, headers, wallet_id, amount=500_000)

    first_charge = client.post(f"/debts/{first['id']}/add-charge", json={"amount": 50_000}, headers=headers)
    assert first_charge.status_code == 201, first_charge.text
    second_charge = client.post(f"/debts/{second['id']}/add-charge", json={"amount": 75_000}, headers=headers)
    assert second_charge.status_code == 201, second_charge.text

    first_detail = client.get(f"/debts/{first['id']}", headers=headers).json()
    first_charge_entry = next(entry for entry in first_detail["ledger_entries"] if entry["entry_type"] == "CHARGE")
    reversed_response = client.post(
        f"/debts/{first['id']}/ledger/{first_charge_entry['id']}/reverse",
        json={"note": "Reverse first debt charge"},
        headers=headers,
    )
    assert reversed_response.status_code == 200, reversed_response.text


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
    assert payload["total_paid"] == 0
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
    assert "status" not in payload
    assert payload["lifecycle_status"] == "CLOSED"
    assert payload["remaining_amount"] == 0
    assert payload["total_paid"] == 0

    detail = client.get(f"/debts/{debt['id']}", headers=headers)
    assert detail.json()["total_paid"] == 0
    forgiveness = [entry for entry in detail.json()["ledger_entries"] if entry["entry_type"] == "FORGIVENESS"]
    assert len(forgiveness) == 1
    assert forgiveness[0]["amount_delta"] == -1_000_000


# ── Ticket 1: derived lifecycle / time-status / timezone boundary ──────────


def test_derived_lifecycle_open_when_remaining_positive(client):
    headers = create_user_and_token(client, "lifecycle1", "lifecycle1@example.com", "Password123!")
    wallet_id = _default_wallet_id(client, headers)
    debt = _create_transferred_debt(client, headers, wallet_id, amount=500_000)
    assert debt["lifecycle_status"] == "OPEN"
    assert debt["remaining_amount"] == 500_000


def test_derived_lifecycle_closed_when_remaining_zero(client):
    headers = create_user_and_token(client, "lifecycle2", "lifecycle2@example.com", "Password123!")
    wallet_id = _default_wallet_id(client, headers)
    debt = _create_transferred_debt(client, headers, wallet_id, amount=500_000)
    forgiven = client.post(f"/debts/{debt['id']}/forgive", headers=headers)
    assert forgiven.status_code == 200
    assert forgiven.json()["lifecycle_status"] == "CLOSED"
    assert forgiven.json()["remaining_amount"] == 0
    assert forgiven.json()["time_status"] is None


def test_time_status_on_track_when_due_today_or_future(client):
    headers = create_user_and_token(client, "timestatus1", "timestatus1@example.com", "Password123!")
    wallet_id = _default_wallet_id(client, headers)
    today = user_timezone_today()
    future = (today + timedelta(days=30)).isoformat()
    response = client.post(
        "/debts",
        json={
            "debt_type": "OWING",
            "counterparty_name": "Test",
            "initial_amount": 200_000,
            "currency": "UZS",
            "date": today.isoformat(),
            "expected_return_date": future,
            "is_money_transferred": True,
            "initial_wallet_id": wallet_id,
        },
        headers=headers,
    )
    assert response.status_code == 201, response.text
    debt = response.json()
    assert debt["lifecycle_status"] == "OPEN"
    assert debt["time_status"] == "ON_TRACK"


def test_time_status_overdue_when_due_before_local_today(client):
    headers = create_user_and_token(client, "timestatus2", "timestatus2@example.com", "Password123!")
    wallet_id = _default_wallet_id(client, headers)
    today = user_timezone_today()
    past = (today - timedelta(days=1)).isoformat()
    response = client.post(
        "/debts",
        json={
            "debt_type": "OWING",
            "counterparty_name": "Test",
            "initial_amount": 200_000,
            "currency": "UZS",
            "date": past,
            "expected_return_date": past,
            "is_money_transferred": True,
            "initial_wallet_id": wallet_id,
        },
        headers=headers,
    )
    assert response.status_code == 201, response.text
    debt = response.json()
    assert debt["lifecycle_status"] == "OPEN"
    assert debt["time_status"] == "OVERDUE"


def test_closed_debt_has_no_time_status(client):
    headers = create_user_and_token(client, "timestatus3", "timestatus3@example.com", "Password123!")
    wallet_id = _default_wallet_id(client, headers)
    today = user_timezone_today()
    past = (today - timedelta(days=90)).isoformat()
    response = client.post(
        "/debts",
        json={
            "debt_type": "OWING",
            "counterparty_name": "Old settled debt",
            "initial_amount": 100_000,
            "currency": "UZS",
            "date": past,
            "expected_return_date": past,
            "is_money_transferred": True,
            "initial_wallet_id": wallet_id,
        },
        headers=headers,
    )
    assert response.status_code == 201, response.text
    debt_id = response.json()["id"]
    forgiven = client.post(f"/debts/{debt_id}/forgive", headers=headers)
    assert forgiven.status_code == 200
    assert forgiven.json()["lifecycle_status"] == "CLOSED"
    assert forgiven.json()["time_status"] is None


def test_archive_is_independent_from_lifecycle(client):
    headers = create_user_and_token(client, "archive1", "archive1@example.com", "Password123!")
    wallet_id = _default_wallet_id(client, headers)
    debt = _create_transferred_debt(client, headers, wallet_id, amount=500_000)

    # archived + open
    archived = client.post(f"/debts/{debt['id']}/archive", headers=headers)
    assert archived.status_code == 200, archived.text
    assert archived.json()["is_archived"] is True
    assert archived.json()["archived_at"] is not None
    assert archived.json()["lifecycle_status"] == "OPEN"

    # restore clears archive, keeps balance + lifecycle
    restored = client.post(f"/debts/{debt['id']}/restore", headers=headers)
    assert restored.status_code == 200, restored.text
    assert restored.json()["is_archived"] is False
    assert restored.json()["archived_at"] is None
    assert restored.json()["lifecycle_status"] == "OPEN"
    assert restored.json()["remaining_amount"] == 500_000

    # archived + closed
    client.post(f"/debts/{debt['id']}/forgive", headers=headers)
    archived2 = client.post(f"/debts/{debt['id']}/archive", headers=headers)
    assert archived2.status_code == 200, archived2.text
    assert archived2.json()["is_archived"] is True
    assert archived2.json()["lifecycle_status"] == "CLOSED"
    assert archived2.json()["time_status"] is None


def test_timezone_boundary_respects_user_tz(client):
    """Open debts due 'today' in the user's TZ should be ON_TRACK, not overdue,
    even when today in UTC has already passed."""
    headers = create_user_and_token(client, "tzbound1", "tzbound1@example.com", "Password123!")
    wallet_id = _default_wallet_id(client, headers)
    today = user_timezone_today().isoformat()
    response = client.post(
        "/debts",
        json={
            "debt_type": "OWING",
            "counterparty_name": "TZ test",
            "initial_amount": 300_000,
            "currency": "UZS",
            "date": today,
            "expected_return_date": today,
            "is_money_transferred": True,
            "initial_wallet_id": wallet_id,
        },
        headers=headers,
    )
    assert response.status_code == 201, response.text
    debt = response.json()
    assert debt["lifecycle_status"] == "OPEN"
    assert debt["time_status"] == "ON_TRACK", (
        f"Expected ON_TRACK for {today} in {headers.get('X-Timezone', 'Asia/Tashkent')}"
    )

    # List filter confirms the boundary
    listed = client.get(
        "/debts",
        params={"time_status": "ON_TRACK", "include_archived": False},
        headers=headers,
    )
    assert listed.status_code == 200
    on_track_ids = [d["id"] for d in listed.json()["items"]]
    assert debt["id"] in on_track_ids


# ── Ticket 2: product_kind cannot leak through public Debt flows ──────────


def test_product_kind_rejected_in_create(client):
    headers = create_user_and_token(client, "noprod1", "noprod1@example.com", "Password123!")
    wallet_id = _default_wallet_id(client, headers)
    today = user_timezone_today().isoformat()
    response = client.post(
        "/debts",
        json={
            "debt_type": "OWING",
            "counterparty_name": "No product test",
            "initial_amount": 100_000,
            "currency": "UZS",
            "date": today,
            "expected_return_date": today,
            "is_money_transferred": True,
            "initial_wallet_id": wallet_id,
            "product_kind": "BANK_LOAN",
        },
        headers=headers,
    )
    assert response.status_code == 201, response.text
    debt = response.json()
    assert "product_kind" not in debt, f"product_kind leaked: {debt}"


def test_product_kind_rejected_in_update(client):
    headers = create_user_and_token(client, "noprod2", "noprod2@example.com", "Password123!")
    wallet_id = _default_wallet_id(client, headers)
    debt = _create_transferred_debt(client, headers, wallet_id)
    response = client.patch(
        f"/debts/{debt['id']}",
        json={"product_kind": "BANK_LOAN"},
        headers=headers,
    )
    assert response.status_code == 422, response.text


def test_list_and_detail_do_not_expose_product_kind(client):
    headers = create_user_and_token(client, "noprod3", "noprod3@example.com", "Password123!")
    wallet_id = _default_wallet_id(client, headers)
    debt = _create_transferred_debt(client, headers, wallet_id)
    # list
    listed = client.get("/debts", headers=headers)
    for item in listed.json()["items"]:
        assert "product_kind" not in item
    # detail
    detail = client.get(f"/debts/{debt['id']}", headers=headers)
    assert "product_kind" not in detail.json()
    # details (full)
    details = client.get(f"/debts/{debt['id']}/details", headers=headers)
    assert "product_kind" not in details.json()["debt"]


# ── Ticket 3: principal / charges / wallet-movement separation ──────────────


def test_t3_principal_only_creation(client):
    """Principal without opening charges — simplest case."""
    headers = create_user_and_token(client, "t3p1", "t3p1@example.com", "Password123!")
    wallet_id = _default_wallet_id(client, headers)
    today = user_timezone_today().isoformat()
    response = client.post(
        "/debts",
        json={
            "debt_type": "OWING",
            "counterparty_name": "Principal only",
            "initial_amount": 1_000_000,
            "currency": "UZS",
            "date": today,
            "expected_return_date": today,
            "is_money_transferred": True,
            "initial_wallet_id": wallet_id,
        },
        headers=headers,
    )
    assert response.status_code == 201, response.text
    debt = response.json()
    assert debt["initial_amount"] == 1_000_000
    assert debt["remaining_amount"] == 1_000_000
    assert debt["total_charges"] == 0
    assert debt["remaining_principal_amount"] == 1_000_000
    assert debt["remaining_charge_amount"] == 0


def test_t3_principal_plus_opening_charges(client):
    """Principal + opening charges = starting balance."""
    headers = create_user_and_token(client, "t3p2", "t3p2@example.com", "Password123!")
    wallet_id = _default_wallet_id(client, headers)
    today = user_timezone_today().isoformat()
    response = client.post(
        "/debts",
        json={
            "debt_type": "OWING",
            "counterparty_name": "Bank with fees",
            "initial_amount": 5_000_000,
            "opening_charge_amount": 500_000,
            "currency": "UZS",
            "date": today,
            "expected_return_date": today,
            "is_money_transferred": True,
            "initial_wallet_id": wallet_id,
        },
        headers=headers,
    )
    assert response.status_code == 201, response.text
    debt = response.json()
    assert debt["initial_amount"] == 5_000_000
    assert debt["remaining_amount"] == 5_500_000
    assert debt["total_charges"] == 500_000
    assert debt["remaining_principal_amount"] == 5_000_000
    assert debt["remaining_charge_amount"] == 500_000


def test_t3_borrowed_cash_with_upfront_fee(client):
    """Wallet receives principal (5M) but debt = principal + fee (5.5M)."""
    headers = create_user_and_token(client, "t3p3", "t3p3@example.com", "Password123!")
    wallet_id = _default_wallet_id(client, headers)
    today = user_timezone_today().isoformat()
    response = client.post(
        "/debts",
        json={
            "debt_type": "OWING",
            "counterparty_name": "Bank loan with origination fee",
            "initial_amount": 5_000_000,
            "opening_charge_amount": 500_000,
            "currency": "UZS",
            "date": today,
            "expected_return_date": today,
            "is_money_transferred": True,
            "initial_wallet_id": wallet_id,
        },
        headers=headers,
    )
    assert response.status_code == 201, response.text
    debt = response.json()
    # principal = 5M, opening charges = 500k → starting balance = 5.5M
    assert debt["initial_amount"] == 5_000_000
    assert debt["remaining_amount"] == 5_500_000
    # Wallet moved 5M (the principal), not 5.5M
    assert debt["is_money_transferred"] is True

    detail = client.get(f"/debts/{debt['id']}", headers=headers).json()
    entry_types = {e["entry_type"] for e in detail["ledger_entries"]}
    assert "INITIAL" in entry_types
    assert "CHARGE" in entry_types


def test_t3_unpaid_service_bill_no_wallet_movement(client):
    """Unpaid service — no cash moved, expense_category required."""
    headers = create_user_and_token(client, "t3p4", "t3p4@example.com", "Password123!")
    today = user_timezone_today().isoformat()
    response = client.post(
        "/debts",
        json={
            "debt_type": "OWING",
            "counterparty_name": "Mechanic",
            "initial_amount": 700_000,
            "currency": "UZS",
            "date": today,
            "expected_return_date": today,
            "is_money_transferred": False,
            "expense_category": "Transport",
        },
        headers=headers,
    )
    assert response.status_code == 201, response.text
    debt = response.json()
    assert debt["initial_amount"] == 700_000
    assert debt["remaining_amount"] == 700_000
    assert debt["is_money_transferred"] is False
    assert debt["total_charges"] == 0


def test_t3_imported_balance_no_wallet_movement(client):
    """Imported balance — no wallet movement, no expense category needed for OWED."""
    headers = create_user_and_token(client, "t3p5", "t3p5@example.com", "Password123!")
    today = user_timezone_today().isoformat()
    response = client.post(
        "/debts",
        json={
            "debt_type": "OWED",
            "counterparty_name": "Historical receivable",
            "initial_amount": 300_000,
            "origin_kind": "IMPORTED_BALANCE",
            "currency": "UZS",
            "date": today,
            "expected_return_date": today,
            "is_money_transferred": False,
        },
        headers=headers,
    )
    assert response.status_code == 201, response.text
    debt = response.json()
    assert debt["is_money_transferred"] is False
    assert debt["initial_amount"] == 300_000
    assert debt["remaining_amount"] == 300_000


def test_t3_wallet_movement_can_differ_from_balance(client):
    """ADR 0027: wallet movement amount ≠ starting balance."""
    headers = create_user_and_token(client, "t3p6", "t3p6@example.com", "Password123!")
    wallet_id = _default_wallet_id(client, headers)
    today = user_timezone_today().isoformat()
    response = client.post(
        "/debts",
        json={
            "debt_type": "OWING",
            "counterparty_name": "Lender with upfront interest",
            "initial_amount": 1_000_000,
            "opening_charge_amount": 100_000,
            "currency": "UZS",
            "date": today,
            "expected_return_date": today,
            "is_money_transferred": True,
            "initial_wallet_id": wallet_id,
        },
        headers=headers,
    )
    assert response.status_code == 201, response.text
    debt = response.json()
    # Wallet received 1M, but obligation is 1.1M
    assert debt["initial_amount"] == 1_000_000
    assert debt["remaining_amount"] == 1_100_000


# ── Ticket 4: component-aware payment allocation ────────────────────────────


def _t4_setup_debt_charges_budget(client, headers):
    """Ensure a DEBT_CHARGES budget exists so charge payments can post."""
    today = user_timezone_today()
    budget_payload = {
        "category": "Debt Charges",  # enum value string
        "monthly_limit": 10_000_000,
        "budget_year": today.year,
        "budget_month": today.month,
    }
    client.post("/budgets/", json=budget_payload, headers=headers)


def _t4_create_debt_with_charges(client, headers, wallet_id):
    """Create a debt with principal 1M + 200k charges for payment tests."""
    _t4_setup_debt_charges_budget(client, headers)
    today = user_timezone_today().isoformat()
    resp = client.post(
        "/debts",
        json={
            "debt_type": "OWING",
            "counterparty_name": "Component test",
            "initial_amount": 1_000_000,
            "opening_charge_amount": 200_000,
            "currency": "UZS",
            "date": today,
            "expected_return_date": today,
            "is_money_transferred": True,
            "initial_wallet_id": wallet_id,
        },
        headers=headers,
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


def test_t4_automatic_allocation_charges_first(client):
    """Default AUTOMATIC = charges-first (ADR 0027)."""
    headers = create_user_and_token(client, "t4a1", "t4a1@example.com", "Password123!")
    wallet_id = _default_wallet_id(client, headers)
    debt = _t4_create_debt_with_charges(client, headers, wallet_id)
    # Pay 150k — all goes to charges (200k available), 0 to principal
    payment = client.post(
        f"/debts/{debt['id']}/payments",
        json={
            "amount": 150_000,
            "wallet_allocations": [{"wallet_id": wallet_id, "amount": 150_000}],
        },
        headers=headers,
    )
    assert payment.status_code == 201, payment.text
    detail = client.get(f"/debts/{debt['id']}", headers=headers).json()
    # remaining = 1.2M - 150k = 1.05M
    assert detail["remaining_amount"] == 1_050_000
    assert detail["remaining_principal_amount"] == 1_000_000  # unchanged
    assert detail["remaining_charge_amount"] == 50_000  # 200k - 150k


def test_t4_charges_first_explicit(client):
    headers = create_user_and_token(client, "t4a2", "t4a2@example.com", "Password123!")
    wallet_id = _default_wallet_id(client, headers)
    debt = _t4_create_debt_with_charges(client, headers, wallet_id)
    payment = client.post(
        f"/debts/{debt['id']}/payments",
        json={
            "amount": 300_000,
            "allocation_mode": "CHARGES_FIRST",
            "wallet_allocations": [{"wallet_id": wallet_id, "amount": 300_000}],
        },
        headers=headers,
    )
    assert payment.status_code == 201, payment.text
    detail = client.get(f"/debts/{debt['id']}", headers=headers).json()
    assert detail["remaining_amount"] == 900_000
    # 200k charges cleared, then 100k principal
    assert detail["remaining_charge_amount"] == 0
    assert detail["remaining_principal_amount"] == 900_000


def test_t4_principal_first_explicit(client):
    headers = create_user_and_token(client, "t4a3", "t4a3@example.com", "Password123!")
    wallet_id = _default_wallet_id(client, headers)
    debt = _t4_create_debt_with_charges(client, headers, wallet_id)
    payment = client.post(
        f"/debts/{debt['id']}/payments",
        json={
            "amount": 300_000,
            "allocation_mode": "PRINCIPAL_FIRST",
            "wallet_allocations": [{"wallet_id": wallet_id, "amount": 300_000}],
        },
        headers=headers,
    )
    assert payment.status_code == 201, payment.text
    detail = client.get(f"/debts/{debt['id']}", headers=headers).json()
    assert detail["remaining_amount"] == 900_000
    assert detail["remaining_principal_amount"] == 700_000  # 1M - 300k
    assert detail["remaining_charge_amount"] == 200_000  # untouched


def test_t4_custom_split(client):
    headers = create_user_and_token(client, "t4a4", "t4a4@example.com", "Password123!")
    wallet_id = _default_wallet_id(client, headers)
    debt = _t4_create_debt_with_charges(client, headers, wallet_id)
    payment = client.post(
        f"/debts/{debt['id']}/payments",
        json={
            "amount": 300_000,
            "allocation_mode": "CUSTOM",
            "principal_amount": 250_000,
            "charge_amount": 50_000,
            "wallet_allocations": [{"wallet_id": wallet_id, "amount": 300_000}],
        },
        headers=headers,
    )
    assert payment.status_code == 201, payment.text
    detail = client.get(f"/debts/{debt['id']}", headers=headers).json()
    assert detail["remaining_amount"] == 900_000
    assert detail["remaining_principal_amount"] == 750_000
    assert detail["remaining_charge_amount"] == 150_000


def test_t4_custom_split_must_match_total(client):
    headers = create_user_and_token(client, "t4a5", "t4a5@example.com", "Password123!")
    wallet_id = _default_wallet_id(client, headers)
    debt = _t4_create_debt_with_charges(client, headers, wallet_id)
    payment = client.post(
        f"/debts/{debt['id']}/payments",
        json={
            "amount": 300_000,
            "allocation_mode": "CUSTOM",
            "principal_amount": 200_000,
            "charge_amount": 50_000,  # only 250k total, not 300k
            "wallet_allocations": [{"wallet_id": wallet_id, "amount": 300_000}],
        },
        headers=headers,
    )
    assert payment.status_code == 422, payment.text


def test_t4_over_allocation_rejected(client):
    headers = create_user_and_token(client, "t4a6", "t4a6@example.com", "Password123!")
    wallet_id = _default_wallet_id(client, headers)
    debt = _t4_create_debt_with_charges(client, headers, wallet_id)
    # Try to pay more charges than exist
    payment = client.post(
        f"/debts/{debt['id']}/payments",
        json={
            "amount": 500_000,
            "allocation_mode": "CUSTOM",
            "principal_amount": 100_000,
            "charge_amount": 400_000,  # only 200k charges exist
            "wallet_allocations": [{"wallet_id": wallet_id, "amount": 500_000}],
        },
        headers=headers,
    )
    assert payment.status_code == 400, payment.text


def test_t4_payment_ledger_entries_have_component_deltas(client):
    headers = create_user_and_token(client, "t4a7", "t4a7@example.com", "Password123!")
    wallet_id = _default_wallet_id(client, headers)
    debt = _t4_create_debt_with_charges(client, headers, wallet_id)
    payment = client.post(
        f"/debts/{debt['id']}/payments",
        json={
            "amount": 300_000,
            "allocation_mode": "CUSTOM",
            "principal_amount": 200_000,
            "charge_amount": 100_000,
            "wallet_allocations": [{"wallet_id": wallet_id, "amount": 300_000}],
        },
        headers=headers,
    )
    assert payment.status_code == 201, payment.text
    detail = client.get(f"/debts/{debt['id']}", headers=headers).json()
    payments = [e for e in detail["ledger_entries"] if e["entry_type"] == "PAYMENT"]
    principal_deltas = [p["principal_delta"] for p in payments]
    charge_deltas = [p["charge_delta"] for p in payments]
    assert sum(principal_deltas) == -200_000
    assert sum(charge_deltas) == -100_000
