from datetime import timedelta

from tests.helpers import TEST_WALLET_EPOCH, create_budget, create_user_and_token, user_timezone_today
from app import models
from app.services.budget_service import compute_budget_chain


def _default_wallet(client, headers):
    response = client.get("/wallets", headers=headers)
    assert response.status_code == 200, response.text
    return response.json()[0]


def _create_wallet(session, user_id, name="Second Wallet", balance=2_000_000):
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


def _create_transferred_debt(client, headers, wallet_id, **overrides):
    payload = {
        "debt_type": "OWING",
        "counterparty_name": "Bank loan",
        "initial_amount": 1_000_000,
        "currency": "UZS",
        "date": user_timezone_today().isoformat(),
        "expected_return_date": user_timezone_today().isoformat(),
        "is_money_transferred": True,
        "initial_wallet_id": wallet_id,
    }
    payload.update(overrides)
    response = client.post("/debts", json=payload, headers=headers)
    assert response.status_code == 201, response.text
    return response.json()


def _create_receivable_debt(client, headers, **overrides):
    payload = {
        "debt_type": "OWED",
        "counterparty_name": "Ali",
        "initial_amount": 500_000,
        "currency": "UZS",
        "description": "Dinner split",
        "date": user_timezone_today().isoformat(),
        "expected_return_date": user_timezone_today().isoformat(),
        "is_money_transferred": False,
    }
    payload.update(overrides)
    response = client.post("/debts", json=payload, headers=headers)
    assert response.status_code == 201, response.text
    return response.json()


def _create_deferred_expense_debt(client, headers, **overrides):
    payload = {
        "debt_type": "OWING",
        "counterparty_name": "Mom",
        "initial_amount": 150_000,
        "currency": "UZS",
        "description": "Dinner",
        "date": user_timezone_today().isoformat(),
        "expected_return_date": user_timezone_today().isoformat(),
        "is_money_transferred": False,
        "expense_category": "Dining Out",
    }
    payload.update(overrides)
    response = client.post("/debts", json=payload, headers=headers)
    assert response.status_code == 201, response.text
    return response.json()


def _create_payment_plan(client, headers, **overrides):
    payload = {
        "item_name": "Phone",
        "store_or_bank_name": "Phone Store",
        "total_price": 1_200_000,
        "down_payment": 0,
        "months": 12,
        "frequency": "MONTHLY",
        "start_date": user_timezone_today().isoformat(),
        "expense_category": "Electronics",
    }
    payload.update(overrides)
    response = client.post("/payment-plans", json=payload, headers=headers)
    assert response.status_code == 201, response.text
    return response.json()


def test_debt_details_actions_and_multi_wallet_payment(client, session):
    headers = create_user_and_token(client, "debtroutes1", "debtroutes1@example.com", "Password123!")
    default_wallet = _default_wallet(client, headers)
    user = _user(session, "debtroutes1@example.com")
    second_wallet = _create_wallet(session, user.id)
    debt = _create_transferred_debt(client, headers, default_wallet["id"])
    initial_event = (
        session.query(models.FinancialEvent)
        .join(models.EntityLedger, models.EntityLedger.event_id == models.FinancialEvent.id)
        .filter(
            models.EntityLedger.debt_id == debt["id"],
            models.FinancialEvent.reference_type == models.ReferenceType.DEBT_INITIAL,
        )
        .first()
    )
    assert initial_event is not None

    details = client.get(f"/debts/{debt['id']}/details", headers=headers)
    assert details.status_code == 200, details.text
    details_payload = details.json()
    assert details_payload["debt"]["remaining_amount"] == 1_000_000
    assert any(item["action_kind"] == "RECORD_PAYMENT" and item["allowed"] for item in details_payload["actions"])
    assert details_payload["activity"][0]["kind"] == "INITIAL"

    actions = client.get(f"/debts/{debt['id']}/actions", headers=headers)
    assert actions.status_code == 200, actions.text
    assert any(item["action_kind"] == "RECORD_PAYMENT" and item["allowed"] for item in actions.json())

    payment = client.post(
        f"/debts/{debt['id']}/payments",
        json={
            "amount": 300_000,
            "date": user_timezone_today().isoformat(),
            "note": "Split across wallets",
            "wallet_allocations": [
                {"wallet_id": default_wallet["id"], "amount": 100_000},
                {"wallet_id": second_wallet.id, "amount": 200_000},
            ],
        },
        headers=headers,
    )
    assert payment.status_code == 201, payment.text
    payment_payload = payment.json()
    assert payment_payload["amount"] == 300_000
    assert sorted(item["amount"] for item in payment_payload["wallet_allocations"]) == [100_000, 200_000]

    session.expire_all()
    allocations = (
        session.query(models.DebtTransactionWalletAllocation)
        .filter(models.DebtTransactionWalletAllocation.debt_id == debt["id"])
        .all()
    )
    assert sorted(item.amount for item in allocations) == [100_000, 200_000]

    updated = client.get(f"/debts/{debt['id']}/details", headers=headers).json()
    assert updated["debt"]["remaining_amount"] == 700_000
    assert any(item["kind"] == "PAYMENT" for item in updated["activity"])


def test_debt_with_payment_history_cannot_patch_opening_amount(client):
    headers = create_user_and_token(client, "debtroutes_opening", "debtroutes_opening@example.com", "Password123!")
    wallet = _default_wallet(client, headers)
    debt = _create_transferred_debt(client, headers, wallet["id"])

    payment = client.post(
        f"/debts/{debt['id']}/payments",
        json={
            "amount": 300_000,
            "date": user_timezone_today().isoformat(),
            "wallet_allocations": [{"wallet_id": wallet["id"], "amount": 300_000}],
        },
        headers=headers,
    )
    assert payment.status_code == 201, payment.text

    edited = client.patch(
        f"/debts/{debt['id']}",
        json={"initial_amount": 900_000},
        headers=headers,
    )
    assert edited.status_code == 400
    assert edited.json()["detail"] == "debts.update.opening_amount_requires_pristine"

    details = client.get(f"/debts/{debt['id']}/details", headers=headers)
    assert details.status_code == 200, details.text
    assert details.json()["debt"]["initial_amount"] == 1_000_000
    assert details.json()["debt"]["remaining_amount"] == 700_000


def test_generic_debt_update_cannot_change_lifecycle_status(client):
    headers = create_user_and_token(client, "debtroutes_status", "debtroutes_status@example.com", "Password123!")
    wallet = _default_wallet(client, headers)
    debt = _create_transferred_debt(client, headers, wallet["id"])

    updated = client.patch(
        f"/debts/{debt['id']}",
        json={"status": "ARCHIVED"},
        headers=headers,
    )
    assert updated.status_code == 422

    details = client.get(f"/debts/{debt['id']}/details", headers=headers)
    assert details.status_code == 200, details.text
    assert "status" not in details.json()["debt"]
    assert details.json()["debt"]["lifecycle_status"] == "OPEN"


def test_pristine_debt_can_patch_opening_amount_and_safe_metadata(client):
    headers = create_user_and_token(client, "debtroutes_pristine", "debtroutes_pristine@example.com", "Password123!")
    wallet = _default_wallet(client, headers)
    debt = _create_transferred_debt(client, headers, wallet["id"])

    edited = client.patch(
        f"/debts/{debt['id']}",
        json={
            "counterparty_name": "Updated lender",
            "description": "Corrected opening setup",
            "initial_amount": 1_200_000,
        },
        headers=headers,
    )
    assert edited.status_code == 200, edited.text
    payload = edited.json()
    assert payload["counterparty_name"] == "Updated lender"
    assert payload["description"] == "Corrected opening setup"
    assert payload["initial_amount"] == 1_200_000
    assert payload["remaining_amount"] == 1_200_000


def test_payment_plan_creation_does_not_create_managed_debt_contract(client, session):
    headers = create_user_and_token(client, "debtroutes_plan", "debtroutes_plan@example.com", "Password123!")
    user = session.query(models.User).filter_by(email="debtroutes_plan@example.com").one()
    debt_count_before = session.query(models.Debt).filter_by(owner_id=user.id).count()

    plan = _create_payment_plan(client, headers)

    assert plan.get("debt_id") is None
    assert session.query(models.Debt).filter_by(owner_id=user.id).count() == debt_count_before


def test_non_pristine_debt_delete_is_blocked_but_pristine_delete_still_works(client):
    headers = create_user_and_token(client, "debtroutes_delete", "debtroutes_delete@example.com", "Password123!")
    wallet = _default_wallet(client, headers)
    active_debt = _create_transferred_debt(client, headers, wallet["id"])
    pristine_debt = _create_transferred_debt(client, headers, wallet["id"], counterparty_name="Draft loan")

    payment = client.post(
        f"/debts/{active_debt['id']}/payments",
        json={
            "amount": 100_000,
            "date": user_timezone_today().isoformat(),
            "wallet_allocations": [{"wallet_id": wallet["id"], "amount": 100_000}],
        },
        headers=headers,
    )
    assert payment.status_code == 201, payment.text

    blocked = client.delete(f"/debts/{active_debt['id']}", headers=headers)
    assert blocked.status_code == 400
    assert blocked.json()["detail"] == "debts.delete.pristine_required"

    deleted = client.delete(f"/debts/{pristine_debt['id']}", headers=headers)
    assert deleted.status_code == 204, deleted.text


def test_debt_creation_derives_initial_amount_from_wallet_rows(client, session):
    headers = create_user_and_token(client, "debtroutesinitialmulti", "debtroutesinitialmulti@example.com", "Password123!")
    default_wallet = _default_wallet(client, headers)
    user = _user(session, "debtroutesinitialmulti@example.com")
    second_wallet = _create_wallet(session, user.id, name="Cash split", balance=500_000)

    response = client.post(
        "/debts",
        json={
            "debt_type": "OWING",
            "counterparty_name": "Friend",
            "initial_amount": 1,
            "currency": "UZS",
            "date": user_timezone_today().isoformat(),
            "expected_return_date": user_timezone_today().isoformat(),
            "is_money_transferred": True,
            "initial_wallet_allocations": [
                {"wallet_id": default_wallet["id"], "amount": 1_000_000},
                {"wallet_id": second_wallet.id, "amount": 2_000_000},
            ],
        },
        headers=headers,
    )

    assert response.status_code == 201, response.text
    debt = response.json()
    assert debt["initial_amount"] == 3_000_000
    assert debt["remaining_amount"] == 3_000_000
    assert debt["is_money_transferred"] is True
    assert debt["initial_wallet_id"] is None

    session.expire_all()
    wallet_one = session.query(models.Wallet).filter_by(id=default_wallet["id"]).first()
    wallet_two = session.query(models.Wallet).filter_by(id=second_wallet.id).first()
    assert wallet_one.current_balance == default_wallet["current_balance"] + 1_000_000
    assert wallet_two.current_balance == 2_500_000

    event = (
        session.query(models.FinancialEvent)
        .join(models.EntityLedger, models.EntityLedger.event_id == models.FinancialEvent.id)
        .filter(models.EntityLedger.debt_id == debt["id"])
        .first()
    )
    assert event.reference_type == models.ReferenceType.DEBT_INITIAL
    assert sorted(leg.amount for leg in event.wallet_legs) == [1_000_000, 2_000_000]

    initial_entry = session.query(models.DebtLedgerEntry).filter_by(debt_id=debt["id"]).first()
    assert initial_entry.amount_delta == 3_000_000
    assert initial_entry.wallet_id is None
    assert initial_entry.financial_event_id == event.id


def test_formal_bank_debt_disbursement_uses_loan_reference_type(client, session):
    headers = create_user_and_token(client, "debtroutesbankloan", "debtroutesbankloan@example.com", "Password123!")
    wallet = _default_wallet(client, headers)

    response = client.post(
        "/debts",
        json={
            "debt_type": "OWING",
            "counterparty_name": "Bank",
            "initial_amount": 5_000_000,
            "currency": "UZS",
            "date": user_timezone_today().isoformat(),
            "expected_return_date": user_timezone_today().isoformat(),
            "is_money_transferred": True,
            "origin_kind": "CASH_BORROWED",
            "counterparty_kind": "BANK",
            "product_kind": "BANK_LOAN",
            "initial_wallet_allocations": [
                {"wallet_id": wallet["id"], "amount": 5_000_000},
            ],
        },
        headers=headers,
    )

    assert response.status_code == 201, response.text
    debt = response.json()
    event = (
        session.query(models.FinancialEvent)
        .join(models.EntityLedger, models.EntityLedger.event_id == models.FinancialEvent.id)
        .filter(models.EntityLedger.debt_id == debt["id"])
        .first()
    )
    assert event.event_type == models.TransactionType.DEBT_SETTLEMENT
    assert event.reference_type == models.ReferenceType.LOAN_DISBURSEMENT


def test_debt_creation_wallet_rows_imply_money_moved(client):
    headers = create_user_and_token(client, "debtroutesinitialrows", "debtroutesinitialrows@example.com", "Password123!")
    wallet = _default_wallet(client, headers)

    response = client.post(
        "/debts",
        json={
            "debt_type": "OWING",
            "counterparty_name": "Friend",
            "initial_amount": 1,
            "currency": "UZS",
            "date": user_timezone_today().isoformat(),
            "expected_return_date": user_timezone_today().isoformat(),
            "is_money_transferred": False,
            "initial_wallet_allocations": [
                {"wallet_id": wallet["id"], "amount": 750_000},
            ],
        },
        headers=headers,
    )

    assert response.status_code == 201, response.text
    debt = response.json()
    assert debt["is_money_transferred"] is True
    assert debt["initial_amount"] == 750_000
    assert debt["expense_category"] is None


def test_debt_creation_rejects_expected_date_before_debt_date(client):
    headers = create_user_and_token(client, "debtroutesduedate", "debtroutesduedate@example.com", "Password123!")

    response = client.post(
        "/debts",
        json={
            "debt_type": "OWED",
            "counterparty_name": "Ali",
            "initial_amount": 500_000,
            "currency": "UZS",
            "date": "2026-06-03",
            "expected_return_date": "2026-06-02",
            "is_money_transferred": False,
        },
        headers=headers,
    )

    assert response.status_code == 422
    assert "debts.validation.expected_date_before_date" in response.text


def test_debt_creation_rejects_dates_before_supported_boundary(client):
    headers = create_user_and_token(client, "debtroutesmindate", "debtroutesmindate@example.com", "Password123!")

    response = client.post(
        "/debts",
        json={
            "debt_type": "OWED",
            "counterparty_name": "Ali",
            "initial_amount": 500_000,
            "currency": "UZS",
            "date": "2019-12-31",
            "expected_return_date": "2020-01-01",
            "is_money_transferred": False,
        },
        headers=headers,
    )

    assert response.status_code == 422
    assert "validation.date_too_early" in response.text


def test_debt_update_rejects_due_date_before_current_debt_date(client):
    headers = create_user_and_token(client, "debtroutespatchduedate", "debtroutespatchduedate@example.com", "Password123!")
    debt = _create_receivable_debt(
        client,
        headers,
        date="2026-06-03",
        expected_return_date="2026-06-04",
    )

    response = client.patch(
        f"/debts/{debt['id']}",
        json={"expected_return_date": "2026-06-02"},
        headers=headers,
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "debts.validation.expected_date_before_date"


def test_deferred_debt_rejects_financing_context_as_expense_category(client):
    headers = create_user_and_token(client, "debtroutescat1", "debtroutescat1@example.com", "Password123!")

    response = client.post(
        "/debts",
        json={
            "debt_type": "OWING",
            "counterparty_name": "Store",
            "initial_amount": 100_000,
            "currency": "UZS",
            "date": user_timezone_today().isoformat(),
            "expected_return_date": user_timezone_today().isoformat(),
            "is_money_transferred": False,
            "expense_category": "Installments & Debt",
        },
        headers=headers,
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "debts.validation.real_expense_category_required"


def test_receivable_income_debt_requires_income_source(client):
    headers = create_user_and_token(client, "debtroutesincome1", "debtroutesincome1@example.com", "Password123!")

    response = client.post(
        "/debts",
        json={
            "debt_type": "OWED",
            "origin_kind": "RECEIVABLE_INCOME",
            "counterparty_name": "Client",
            "initial_amount": 500_000,
            "currency": "UZS",
            "date": user_timezone_today().isoformat(),
            "expected_return_date": user_timezone_today().isoformat(),
            "is_money_transferred": False,
        },
        headers=headers,
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "debts.validation.income_source.required"


def test_payable_debts_expose_hard_due_and_overdue_warnings(client):
    headers = create_user_and_token(client, "debtrouteswarnings", "debtrouteswarnings@example.com", "Password123!")
    today = user_timezone_today()

    due = _create_deferred_expense_debt(
        client,
        headers,
        counterparty_name="Store due",
        date=today.isoformat(),
        expected_return_date=today.isoformat(),
    )
    overdue_date = today - timedelta(days=2)
    overdue = _create_deferred_expense_debt(
        client,
        headers,
        counterparty_name="Store overdue",
        date=overdue_date.isoformat(),
        expected_return_date=overdue_date.isoformat(),
    )

    listed = client.get("/debts?debt_type=OWING", headers=headers)
    assert listed.status_code == 200, listed.text
    by_id = {item["id"]: item for item in listed.json()["items"]}
    assert "debts.warning.payable_due_hard" in by_id[due["id"]]["workflow_warnings"]
    assert "debts.warning.payable_overdue_hard" not in by_id[due["id"]]["workflow_warnings"]
    assert "debts.warning.payable_overdue_hard" in by_id[overdue["id"]]["workflow_warnings"]
    assert "debts.warning.payable_due_hard" not in by_id[overdue["id"]]["workflow_warnings"]


def test_debt_creation_requires_expected_return_date(client):
    headers = create_user_and_token(client, "debtroutespaydown", "debtroutespaydown@example.com", "Password123!")

    response = client.post(
        "/debts",
        json={
            "debt_type": "OWING",
            "counterparty_name": "Open friend debt",
            "initial_amount": 150_000,
            "currency": "UZS",
            "date": user_timezone_today().isoformat(),
            "is_money_transferred": False,
            "expense_category": "Dining Out",
        },
        headers=headers,
    )

    assert response.status_code == 422
    assert "debts.validation.expected_date_required" in response.text


def test_damage_compensation_i_owe_payment_posts_as_expense(client, session):
    headers = create_user_and_token(client, "debtroutesdamageowe", "debtroutesdamageowe@example.com", "Password123!")
    today = user_timezone_today()
    create_budget(client, headers, category="Electronics", monthly_limit=1_000_000, budget_year=today.year, budget_month=today.month)
    wallet = _default_wallet(client, headers)

    debt_response = client.post(
        "/debts",
        json={
            "debt_type": "OWING",
            "origin_kind": "DAMAGE_COMPENSATION",
            "counterparty_kind": "PERSON",
            "product_kind": "PERSONAL_REIMBURSEMENT",
            "counterparty_name": "Neighbor",
            "initial_amount": 800_000,
            "currency": "UZS",
            "date": today.isoformat(),
            "expected_return_date": today.isoformat(),
            "is_money_transferred": False,
            "expense_category": "Electronics",
        },
        headers=headers,
    )
    assert debt_response.status_code == 201, debt_response.text
    debt = debt_response.json()

    payment = client.post(
        f"/debts/{debt['id']}/payments",
        json={
            "amount": 300_000,
            "date": today.isoformat(),
            "wallet_allocations": [{"wallet_id": wallet["id"], "amount": 300_000}],
        },
        headers=headers,
    )
    assert payment.status_code == 201, payment.text
    transaction_id = payment.json()["id"]

    event = (
        session.query(models.FinancialEvent)
        .join(models.EntityLedger, models.EntityLedger.event_id == models.FinancialEvent.id)
        .filter(
            models.EntityLedger.debt_id == debt["id"],
            models.FinancialEvent.description.like(f"%[debt_txn:{transaction_id}]%"),
        )
        .one()
    )
    assert event.event_type == models.TransactionType.EXPENSE
    assert event.reference_type == models.ReferenceType.DAMAGE_COMPENSATION
    assert event.entity_legs[0].category == models.ExpenseCategory.ELECTRONICS


def test_damage_compensation_owed_to_me_payment_is_not_income(client, session):
    headers = create_user_and_token(client, "debtroutesdamageowed", "debtroutesdamageowed@example.com", "Password123!")
    wallet = _default_wallet(client, headers)

    debt_response = client.post(
        "/debts",
        json={
            "debt_type": "OWED",
            "origin_kind": "DAMAGE_COMPENSATION",
            "counterparty_kind": "PERSON",
            "product_kind": "PERSONAL_REIMBURSEMENT",
            "counterparty_name": "Friend",
            "initial_amount": 600_000,
            "currency": "UZS",
            "date": user_timezone_today().isoformat(),
            "expected_return_date": user_timezone_today().isoformat(),
            "is_money_transferred": False,
        },
        headers=headers,
    )
    assert debt_response.status_code == 201, debt_response.text
    debt = debt_response.json()

    payment = client.post(
        f"/debts/{debt['id']}/payments",
        json={
            "amount": 200_000,
            "date": user_timezone_today().isoformat(),
            "wallet_allocations": [{"wallet_id": wallet["id"], "amount": 200_000}],
        },
        headers=headers,
    )
    assert payment.status_code == 201, payment.text
    transaction_id = payment.json()["id"]

    event = (
        session.query(models.FinancialEvent)
        .join(models.EntityLedger, models.EntityLedger.event_id == models.FinancialEvent.id)
        .filter(
            models.EntityLedger.debt_id == debt["id"],
            models.FinancialEvent.description.like(f"%[debt_txn:{transaction_id}]%"),
        )
        .one()
    )
    assert event.event_type == models.TransactionType.DEBT_SETTLEMENT
    assert event.reference_type == models.ReferenceType.DAMAGE_COMPENSATION
    assert event.entity_legs[0].income_source_id is None


def test_multi_wallet_payment_posts_owing_charge_as_expense_by_wallet_order(client, session):
    headers = create_user_and_token(client, "debtroutescharge1", "debtroutescharge1@example.com", "Password123!")
    today = user_timezone_today()
    create_budget(client, headers, category="Debt Charges", monthly_limit=500_000, budget_year=today.year, budget_month=today.month)
    default_wallet = _default_wallet(client, headers)
    user = _user(session, "debtroutescharge1@example.com")
    second_wallet = _create_wallet(session, user.id, name="Charge Wallet")
    debt = _create_transferred_debt(client, headers, default_wallet["id"], initial_amount=100_000)

    charge = client.post(
        f"/debts/{debt['id']}/add-charge",
        json={"amount": 50_000, "reason": "Interest"},
        headers=headers,
    )
    assert charge.status_code == 201, charge.text

    payment = client.post(
        f"/debts/{debt['id']}/payments",
        json={
            "amount": 150_000,
            "date": user_timezone_today().isoformat(),
            "note": "Two-wallet payoff",
            "wallet_allocations": [
                {"wallet_id": default_wallet["id"], "amount": 75_000},
                {"wallet_id": second_wallet.id, "amount": 75_000},
            ],
        },
        headers=headers,
    )
    assert payment.status_code == 201, payment.text
    transaction_id = payment.json()["id"]

    session.expire_all()
    events = (
        session.query(models.FinancialEvent)
        .join(models.EntityLedger, models.EntityLedger.event_id == models.FinancialEvent.id)
        .filter(
            models.EntityLedger.debt_id == debt["id"],
            models.FinancialEvent.description.like(f"%[debt_txn:{transaction_id}]%"),
        )
        .order_by(models.FinancialEvent.id.asc())
        .all()
    )
    assert [event.event_type for event in events] == [
        models.TransactionType.DEBT_SETTLEMENT,
        models.TransactionType.EXPENSE,
    ]

    principal_event, charge_event = events
    principal_legs = {leg.wallet_id: int(leg.amount) for leg in principal_event.wallet_legs}
    charge_legs = {leg.wallet_id: int(leg.amount) for leg in charge_event.wallet_legs}
    assert principal_legs == {default_wallet["id"]: -75_000, second_wallet.id: -25_000}
    assert charge_legs == {second_wallet.id: -50_000}
    assert charge_event.reference_type == models.ReferenceType.DEBT_CHARGE
    assert charge_event.entity_legs[0].category == models.ExpenseCategory.DEBT_CHARGES
    assert charge_event.entity_legs[0].budget_id is not None
    assert int(charge_event.entity_legs[0].amount) == 50_000

    payment_entries = (
        session.query(models.DebtLedgerEntry)
        .filter(
            models.DebtLedgerEntry.debt_id == debt["id"],
            models.DebtLedgerEntry.source_debt_transaction_id == transaction_id,
        )
        .order_by(models.DebtLedgerEntry.id.asc())
        .all()
    )
    assert [(entry.principal_delta, entry.charge_delta) for entry in payment_entries] == [
        (-100_000, 0),
        (0, -50_000),
    ]


def test_multi_wallet_payment_posts_owed_charge_as_income_by_wallet_order(client, session):
    headers = create_user_and_token(client, "debtroutescharge2", "debtroutescharge2@example.com", "Password123!")
    default_wallet = _default_wallet(client, headers)
    user = _user(session, "debtroutescharge2@example.com")
    second_wallet = _create_wallet(session, user.id, name="Income Wallet")
    debt = _create_transferred_debt(
        client,
        headers,
        default_wallet["id"],
        debt_type="OWED",
        counterparty_name="Client",
        initial_amount=100_000,
    )

    charge = client.post(
        f"/debts/{debt['id']}/add-charge",
        json={"amount": 50_000, "reason": "Late fee"},
        headers=headers,
    )
    assert charge.status_code == 201, charge.text

    payment = client.post(
        f"/debts/{debt['id']}/payments",
        json={
            "amount": 150_000,
            "date": user_timezone_today().isoformat(),
            "note": "Client payoff",
            "wallet_allocations": [
                {"wallet_id": default_wallet["id"], "amount": 75_000},
                {"wallet_id": second_wallet.id, "amount": 75_000},
            ],
        },
        headers=headers,
    )
    assert payment.status_code == 201, payment.text
    transaction_id = payment.json()["id"]

    session.expire_all()
    events = (
        session.query(models.FinancialEvent)
        .join(models.EntityLedger, models.EntityLedger.event_id == models.FinancialEvent.id)
        .filter(
            models.EntityLedger.debt_id == debt["id"],
            models.FinancialEvent.description.like(f"%[debt_txn:{transaction_id}]%"),
        )
        .order_by(models.FinancialEvent.id.asc())
        .all()
    )
    assert [event.event_type for event in events] == [
        models.TransactionType.DEBT_SETTLEMENT,
        models.TransactionType.INCOME,
    ]

    principal_event, charge_event = events
    principal_legs = {leg.wallet_id: int(leg.amount) for leg in principal_event.wallet_legs}
    charge_legs = {leg.wallet_id: int(leg.amount) for leg in charge_event.wallet_legs}
    assert principal_legs == {default_wallet["id"]: 75_000, second_wallet.id: 25_000}
    assert charge_legs == {second_wallet.id: 50_000}
    assert charge_event.reference_type == models.ReferenceType.DEBT_CHARGE
    assert int(charge_event.entity_legs[0].amount) == 50_000


def test_deferred_debt_payment_expenses_link_budgets_and_debt_details(client, session):
    headers = create_user_and_token(client, "debtroutesbudget1", "debtroutesbudget1@example.com", "Password123!")
    today = user_timezone_today()
    create_budget(client, headers, category="Dining Out", monthly_limit=500_000, budget_year=today.year, budget_month=today.month)
    create_budget(client, headers, category="Debt Charges", monthly_limit=500_000, budget_year=today.year, budget_month=today.month)
    default_wallet = _default_wallet(client, headers)
    user = _user(session, "debtroutesbudget1@example.com")
    second_wallet = _create_wallet(session, user.id, name="Second Pay Wallet")
    debt = _create_deferred_expense_debt(client, headers)

    charge = client.post(
        f"/debts/{debt['id']}/add-charge",
        json={"amount": 20_000, "reason": "Late charge"},
        headers=headers,
    )
    assert charge.status_code == 201, charge.text

    payment = client.post(
        f"/debts/{debt['id']}/payments",
        json={
            "amount": 170_000,
            "date": today.isoformat(),
            "note": "Deferred dinner payoff",
            "wallet_allocations": [
                {"wallet_id": default_wallet["id"], "amount": 90_000},
                {"wallet_id": second_wallet.id, "amount": 80_000},
            ],
        },
        headers=headers,
    )
    assert payment.status_code == 201, payment.text
    transaction_id = payment.json()["id"]

    session.expire_all()
    events = (
        session.query(models.FinancialEvent)
        .join(models.EntityLedger, models.EntityLedger.event_id == models.FinancialEvent.id)
        .filter(
            models.EntityLedger.debt_id == debt["id"],
            models.FinancialEvent.description.like(f"%[debt_txn:{transaction_id}]%"),
        )
        .order_by(models.FinancialEvent.id.asc())
        .all()
    )
    assert [event.event_type for event in events] == [
        models.TransactionType.EXPENSE,
        models.TransactionType.EXPENSE,
    ]

    principal_event, charge_event = events
    assert principal_event.reference_type == models.ReferenceType.DEBT_EXPENSE
    assert charge_event.reference_type == models.ReferenceType.DEBT_CHARGE
    assert principal_event.entity_legs[0].category == models.ExpenseCategory.DINING_OUT
    assert charge_event.entity_legs[0].category == models.ExpenseCategory.DEBT_CHARGES
    assert principal_event.entity_legs[0].budget_id is not None
    assert charge_event.entity_legs[0].budget_id is not None
    assert principal_event.entity_legs[0].debt_id == debt["id"]
    assert charge_event.entity_legs[0].debt_id == debt["id"]

    dining_budget = (
        session.query(models.Budget)
        .filter_by(owner_id=user.id, category=models.ExpenseCategory.DINING_OUT, budget_year=today.year, budget_month=today.month)
        .one()
    )
    charge_budget = (
        session.query(models.Budget)
        .filter_by(owner_id=user.id, category=models.ExpenseCategory.DEBT_CHARGES, budget_year=today.year, budget_month=today.month)
        .one()
    )
    spent = {
        item.budget.category: item.spent
        for item in compute_budget_chain(session, user.id, [dining_budget, charge_budget])
    }
    assert spent[models.ExpenseCategory.DINING_OUT] == 150_000
    assert spent[models.ExpenseCategory.DEBT_CHARGES] == 20_000

    principal_detail = client.get(f"/expenses/{principal_event.id}/detail", headers=headers)
    assert principal_detail.status_code == 200, principal_detail.text
    assert [item["id"] for item in principal_detail.json()["related_debts"]] == [debt["id"]]
    charge_detail = client.get(f"/expenses/{charge_event.id}/detail", headers=headers)
    assert charge_detail.status_code == 200, charge_detail.text
    assert [item["id"] for item in charge_detail.json()["related_debts"]] == [debt["id"]]

    feed = client.get("/expenses/?sort=newest&limit=2", headers=headers)
    assert feed.status_code == 200, feed.text
    feed_expense_ids = [item["expense"]["id"] for item in feed.json()["items"]]
    assert feed_expense_ids == sorted(feed_expense_ids, reverse=True)


def test_partial_and_formal_debts_use_component_aware_forgiveness(client, session):
    headers = create_user_and_token(client, "debtroutes2", "debtroutes2@example.com", "Password123!")
    wallet = _default_wallet(client, headers)

    personal_debt = _create_receivable_debt(client, headers)
    partial = client.post(
        f"/debts/{personal_debt['id']}/forgiveness",
        json={"amount": 100_000, "component": "PRINCIPAL", "note": "No need to pay this part"},
        headers=headers,
    )
    assert partial.status_code == 200, partial.text
    assert partial.json()["remaining_amount"] == 400_000
    assert partial.json()["lifecycle_status"] == "OPEN"
    assert "status" not in partial.json()

    formal_debt = _create_transferred_debt(
        client,
        headers,
        wallet["id"],
        counterparty_kind="BANK",
        product_kind="BANK_LOAN",
    )
    forgiven = client.post(
        f"/debts/{formal_debt['id']}/forgiveness",
        json={"amount": 100_000, "component": "PRINCIPAL"},
        headers=headers,
    )
    assert forgiven.status_code == 200, forgiven.text
    assert forgiven.json()["remaining_amount"] == 900_000
    assert forgiven.json()["lifecycle_status"] == "OPEN"


def test_balance_adjustment_reversal_and_formal_details(client, session):
    headers = create_user_and_token(client, "debtroutes3", "debtroutes3@example.com", "Password123!")
    wallet = _default_wallet(client, headers)
    debt = _create_transferred_debt(client, headers, wallet["id"])

    adjusted = client.post(
        f"/debts/{debt['id']}/balance-adjustments",
        json={"confirmed_balance": 800_000, "note": "Statement correction"},
        headers=headers,
    )
    assert adjusted.status_code == 200, adjusted.text
    assert adjusted.json()["remaining_amount"] == 800_000

    details = client.get(f"/debts/{debt['id']}/details", headers=headers).json()
    adjustment = next(item for item in details["activity"] if item["kind"] == "ADJUSTMENT")
    reversed_response = client.post(
        f"/debts/{debt['id']}/ledger/{adjustment['ledger_entry_id']}/reverse",
        json={"note": "Correction was wrong"},
        headers=headers,
    )
    assert reversed_response.status_code == 200, reversed_response.text
    assert reversed_response.json()["remaining_amount"] == 1_000_000

    formal = client.patch(
        f"/debts/{debt['id']}/formal-details",
        json={
            "institution_name": "Kapitalbank",
            "contract_number": "LN-2026-1",
            "statement_balance": 1_000_000,
            "statement_balance_date": user_timezone_today().isoformat(),
        },
        headers=headers,
    )
    assert formal.status_code == 200, formal.text
    assert formal.json()["institution_name"] == "Kapitalbank"

    details_after = client.get(f"/debts/{debt['id']}/details", headers=headers).json()
    assert details_after["formal_details"]["contract_number"] == "LN-2026-1"
