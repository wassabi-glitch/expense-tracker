from datetime import date, timedelta

from app import models
from tests.helpers import create_budget, create_user_and_token, user_timezone_today


def _default_wallet(client, headers):
    response = client.get("/wallets", headers=headers)
    assert response.status_code == 200, response.text
    return response.json()[0]


def _create_installment(client, headers, **overrides):
    payload = {
        "item_name": "Phone",
        "store_or_bank_name": "Phone Store",
        "total_price": 5_400_000,
        "down_payment": 0,
        "months": 12,
        "frequency": "MONTHLY",
        "start_date": user_timezone_today().isoformat(),
        "expense_category": "Electronics",
    }
    payload.update(overrides)
    response = client.post("/installments", json=payload, headers=headers)
    assert response.status_code == 201, response.text
    return response.json()


def _create_installment_budgets(client, headers):
    today = user_timezone_today()
    create_budget(
        client,
        headers,
        category="Electronics",
        monthly_limit=9_000_000,
        budget_year=today.year,
        budget_month=today.month,
    )
    create_budget(
        client,
        headers,
        category="Debt Charges",
        monthly_limit=1_000_000,
        budget_year=today.year,
        budget_month=today.month,
    )


def _make_premium(client, headers):
    premium = client.post("/users/me/toggle-premium", headers=headers)
    assert premium.status_code == 200


def _setup_goal_wallet(client, headers, initial_balance=2_000_000):
    onboard = client.post(
        "/users/me/onboarding",
        json={
            "life_statuses": ["employed"],
            "wallets": [
                {
                    "name": "Savings",
                    "wallet_type": "SAVINGS",
                    "initial_balance": initial_balance,
                    "can_fund_goals": True,
                }
            ],
        },
        headers=headers,
    )
    assert onboard.status_code == 200
    _make_premium(client, headers)
    wallets = client.get("/wallets", headers=headers)
    assert wallets.status_code == 200
    return wallets.json()[0]["id"]


def _sorted_payments(plan_payload):
    return sorted(plan_payload["payments"], key=lambda item: (item["due_date"], item["id"]))


def test_installment_creation_creates_linked_debt_and_details(client):
    headers = create_user_and_token(client, "installroutes1", "installroutes1@example.com", "Password123!")

    plan = _create_installment(client, headers)
    assert plan["debt_id"] is not None
    assert plan["remaining_amount"] == 5_400_000
    assert len(plan["payments"]) == 12
    assert {payment["amount"] for payment in plan["payments"]} == {450_000}

    details = client.get(f"/installments/{plan['id']}/details", headers=headers)
    assert details.status_code == 200, details.text
    payload = details.json()
    assert payload["debt"]["remaining_amount"] == 5_400_000
    assert payload["debt"]["product_kind"] == "STORE_INSTALLMENT"
    assert payload["debt_activity"][0]["kind"] == "INITIAL"
    assert any(item["action_kind"] == "RECORD_PAYMENT" and item["allowed"] for item in payload["debt_actions"])

    debt_actions = client.get(f"/debts/{plan['debt_id']}/actions", headers=headers)
    assert debt_actions.status_code == 200, debt_actions.text
    debt_payment_action = next(item for item in debt_actions.json() if item["action_kind"] == "RECORD_PAYMENT")
    assert debt_payment_action["allowed"] is False
    assert debt_payment_action["reason_code"] == "debts.policy.managed_by_payment_plan"
    assert debt_payment_action["details"]["installment_plan_id"] == plan["id"]


def test_bank_loan_payment_plan_disbursement_creates_debt_flow_event(client, session):
    headers = create_user_and_token(client, "installroutesloan", "installroutesloan@example.com", "Password123!")
    wallet = _default_wallet(client, headers)
    before_balance = wallet["current_balance"]

    plan = _create_installment(
        client,
        headers,
        item_name="Microloan",
        store_or_bank_name="TBC Bank",
        plan_type="BANK_LOAN",
        total_price=5_000_000,
        down_payment=0,
        months=10,
        expense_category="Utilities",
        loan_disbursement_wallet_id=wallet["id"],
    )

    assert plan["debt_id"] is not None
    assert plan["remaining_amount"] == 5_000_000

    refreshed_wallet = client.get("/wallets", headers=headers).json()[0]
    assert refreshed_wallet["current_balance"] == before_balance + 5_000_000

    event = session.query(models.FinancialEvent).filter_by(reference_type=models.ReferenceType.LOAN_DISBURSEMENT).first()
    assert event is not None
    assert event.event_type == models.TransactionType.DEBT_SETTLEMENT

    details = client.get(f"/installments/{plan['id']}/details", headers=headers).json()
    debt = details["debt"]
    assert debt["product_kind"] == "BANK_LOAN"
    assert debt["origin_kind"] == "CASH_BORROWED"
    debt_model = session.query(models.Debt).filter_by(id=plan["debt_id"]).first()
    assert debt_model.is_money_transferred is True
    assert debt_model.initial_wallet_id == wallet["id"]
    assert details["debt_activity"][0]["financial_event_id"] == event.id


def test_bank_loan_disbursement_rejects_credit_wallet(client, session):
    headers = create_user_and_token(client, "installroutescredit", "installroutescredit@example.com", "Password123!")
    user = session.query(models.User).filter_by(email="installroutescredit@example.com").first()
    credit_wallet = models.Wallet(
        owner_id=user.id,
        name="Credit Card",
        wallet_type=models.WalletType.CREDIT,
        accounting_type=models.AccountingType.LIABILITY,
        initial_balance=0,
        current_balance=0,
        credit_limit=10_000_000,
    )
    session.add(credit_wallet)
    session.commit()
    session.refresh(credit_wallet)

    response = client.post(
        "/installments",
        json={
            "item_name": "Microloan",
            "store_or_bank_name": "Bank",
            "plan_type": "BANK_LOAN",
            "total_price": 5_000_000,
            "down_payment": 0,
            "months": 10,
            "frequency": "MONTHLY",
            "start_date": user_timezone_today().isoformat(),
            "expense_category": "Utilities",
            "loan_disbursement_wallet_id": credit_wallet.id,
        },
        headers=headers,
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "installments.loan_disbursement_wallet_not_allowed"


def test_payment_plan_type_and_new_frequencies_are_persisted(client):
    headers = create_user_and_token(client, "installroutesfreq", "installroutesfreq@example.com", "Password123!")
    start = user_timezone_today()

    auto_plan = _create_installment(
        client,
        headers,
        item_name="Car",
        store_or_bank_name="Bank",
        plan_type="AUTO_LOAN",
        frequency="BIWEEKLY",
        total_price=1_000_000,
        months=2,
        expense_category="Transport",
    )
    auto_payments = _sorted_payments(auto_plan)

    assert auto_plan["plan_type"] == "AUTO_LOAN"
    assert auto_plan["payment_count"] == 2
    assert auto_plan["regular_payment_amount"] == 500_000
    assert auto_plan["schedule_rule"]["frequency"] == "BIWEEKLY"
    assert auto_payments[0]["due_date"] == (start + timedelta(weeks=2)).isoformat()
    assert auto_payments[1]["due_date"] == (start + timedelta(weeks=4)).isoformat()

    auto_details = client.get(f"/installments/{auto_plan['id']}/details", headers=headers)
    assert auto_details.status_code == 200, auto_details.text
    assert auto_details.json()["debt"]["product_kind"] == "CAR_LOAN"

    mortgage_plan = _create_installment(
        client,
        headers,
        item_name="Apartment",
        store_or_bank_name="Mortgage Bank",
        plan_type="MORTGAGE",
        frequency="QUARTERLY",
        start_date=date(2026, 1, 31).isoformat(),
        total_price=2_000_000,
        months=2,
        expense_category=None,
    )
    mortgage_payments = _sorted_payments(mortgage_plan)

    assert mortgage_plan["plan_type"] == "MORTGAGE"
    assert mortgage_plan["expense_category"] == "Housing"
    assert mortgage_payments[0]["due_date"] == date(2026, 4, 30).isoformat()
    assert mortgage_payments[1]["due_date"] == date(2026, 7, 31).isoformat()


def test_payment_plan_requires_real_category_when_type_has_no_safe_default(client):
    headers = create_user_and_token(client, "installroutescat", "installroutescat@example.com", "Password123!")

    response = client.post(
        "/installments",
        json={
            "item_name": "Sofa",
            "store_or_bank_name": "Store",
            "plan_type": "STORE_INSTALLMENT",
            "total_price": 1_000_000,
            "down_payment": 0,
            "months": 2,
            "frequency": "MONTHLY",
            "start_date": user_timezone_today().isoformat(),
            "expense_category": None,
        },
        headers=headers,
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "installments.validation.real_expense_category_required"


def test_legacy_payment_plan_without_real_category_cannot_post_deprecated_expense(client, session):
    headers = create_user_and_token(client, "installrouteslegacycat", "installrouteslegacycat@example.com", "Password123!")
    user = session.query(models.User).filter_by(email="installrouteslegacycat@example.com").first()
    assert user is not None
    wallet = _default_wallet(client, headers)
    today = user_timezone_today()

    plan = models.InstallmentPlan(
        owner_id=user.id,
        item_name="Legacy sofa",
        store_or_bank_name="Old Store",
        plan_type=models.PaymentPlanType.STORE_INSTALLMENT,
        total_price=300_000,
        down_payment=0,
        remaining_amount=300_000,
        months=3,
        payment_count=3,
        frequency=models.InstallmentFrequency.MONTHLY,
        monthly_payment_amount=100_000,
        regular_payment_amount=100_000,
        schedule_rule={"source": "LEGACY"},
        status=models.InstallmentStatus.ACTIVE,
        start_date=today,
        expense_category=None,
    )
    session.add(plan)
    session.flush()
    session.add(
        models.InstallmentPayment(
            owner_id=user.id,
            plan_id=plan.id,
            amount=100_000,
            due_date=today,
            component_type=models.InstallmentPaymentComponentType.PRINCIPAL,
            status=models.InstallmentPaymentStatus.PENDING,
        )
    )
    session.commit()
    plan_id = plan.id

    response = client.post(
        f"/installments/{plan_id}/payments",
        json={
            "amount": 100_000,
            "wallet_allocations": [{"wallet_id": wallet["id"], "amount": 100_000}],
        },
        headers=headers,
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "installments.validation.real_expense_category_required"
    session.expire_all()
    refreshed_plan = session.query(models.InstallmentPlan).filter_by(id=plan_id).one()
    assert refreshed_plan.debt_id is None
    deprecated_legs = (
        session.query(models.EntityLedger)
        .join(models.FinancialEvent, models.FinancialEvent.id == models.EntityLedger.event_id)
        .filter(
            models.FinancialEvent.owner_id == user.id,
            models.EntityLedger.category == models.ExpenseCategory.INSTALLMENTS_DEBT,
        )
        .all()
    )
    assert deprecated_legs == []


def test_legacy_mark_paid_without_real_category_cannot_default_to_deprecated_category(client, session):
    headers = create_user_and_token(client, "installrouteslegacymarkpaid", "installrouteslegacymarkpaid@example.com", "Password123!")
    user = session.query(models.User).filter_by(email="installrouteslegacymarkpaid@example.com").first()
    assert user is not None
    wallet = _default_wallet(client, headers)
    today = user_timezone_today()

    debt = models.Debt(
        owner_id=user.id,
        debt_type=models.DebtType.OWING,
        origin_kind=models.DebtOriginKind.FINANCED_ASSET_PURCHASE,
        counterparty_kind=models.DebtCounterpartyKind.STORE,
        product_kind=models.DebtProductKind.STORE_INSTALLMENT,
        counterparty_name="Old Store",
        initial_amount=100_000,
        remaining_amount=100_000,
        currency="UZS",
        status=models.DebtStatus.ACTIVE,
        date=today,
        is_money_transferred=False,
        expense_category=None,
    )
    session.add(debt)
    session.flush()
    plan = models.InstallmentPlan(
        owner_id=user.id,
        debt_id=debt.id,
        item_name="Legacy chair",
        store_or_bank_name="Old Store",
        plan_type=models.PaymentPlanType.STORE_INSTALLMENT,
        total_price=100_000,
        down_payment=0,
        remaining_amount=100_000,
        months=1,
        payment_count=1,
        frequency=models.InstallmentFrequency.MONTHLY,
        monthly_payment_amount=100_000,
        regular_payment_amount=100_000,
        schedule_rule={"source": "LEGACY"},
        status=models.InstallmentStatus.ACTIVE,
        start_date=today,
        expense_category=None,
    )
    session.add(plan)
    session.flush()
    payment = models.InstallmentPayment(
        owner_id=user.id,
        plan_id=plan.id,
        amount=100_000,
        due_date=today,
        component_type=models.InstallmentPaymentComponentType.PRINCIPAL,
        status=models.InstallmentPaymentStatus.PENDING,
    )
    session.add(payment)
    session.commit()
    payment_id = payment.id
    plan_id = plan.id
    debt_id = debt.id

    response = client.post(
        f"/installments/payments/{payment_id}/mark-paid",
        json={"wallet_allocations": [{"wallet_id": wallet["id"], "amount": 100_000}]},
        headers=headers,
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "installments.validation.real_expense_category_required"
    session.expire_all()
    refreshed_plan = session.query(models.InstallmentPlan).filter_by(id=plan_id).one()
    refreshed_debt = session.query(models.Debt).filter_by(id=debt_id).one()
    assert refreshed_plan.expense_category is None
    assert refreshed_debt.expense_category is None
    deprecated_legs = (
        session.query(models.EntityLedger)
        .join(models.FinancialEvent, models.FinancialEvent.id == models.EntityLedger.event_id)
        .filter(
            models.FinancialEvent.owner_id == user.id,
            models.EntityLedger.category == models.ExpenseCategory.INSTALLMENTS_DEBT,
        )
        .all()
    )
    assert deprecated_legs == []


def test_installment_partial_and_advance_payment_allocates_across_schedule(client, session):
    headers = create_user_and_token(client, "installroutes2", "installroutes2@example.com", "Password123!")
    _create_installment_budgets(client, headers)
    wallet = _default_wallet(client, headers)
    plan = _create_installment(client, headers)

    partial = client.post(
        f"/installments/{plan['id']}/payments",
        json={
            "amount": 300_000,
            "wallet_allocations": [{"wallet_id": wallet["id"], "amount": 300_000}],
            "note": "Paid what I had",
        },
        headers=headers,
    )
    assert partial.status_code == 201, partial.text
    payments_after_partial = _sorted_payments(partial.json()["plan"])
    assert partial.json()["debt"]["remaining_amount"] == 5_100_000
    assert payments_after_partial[0]["status"] == "PARTIAL"
    assert payments_after_partial[0]["paid_amount"] == 300_000
    payment_event = session.query(models.FinancialEvent).filter_by(id=payments_after_partial[0]["event_id"]).first()
    assert payment_event.reference_type == models.ReferenceType.INSTALLMENT_PAYMENT

    advance = client.post(
        f"/installments/{plan['id']}/payments",
        json={
            "amount": 1_000_000,
            "wallet_allocations": [{"wallet_id": wallet["id"], "amount": 1_000_000}],
            "note": "Advance payment",
        },
        headers=headers,
    )
    assert advance.status_code == 201, advance.text
    payload = advance.json()
    payments = _sorted_payments(payload["plan"])

    assert payload["debt"]["remaining_amount"] == 4_100_000
    assert payments[0]["status"] == "PAID"
    assert payments[0]["paid_amount"] == 450_000
    assert payments[1]["status"] == "PAID"
    assert payments[1]["paid_amount"] == 450_000
    assert payments[2]["status"] == "PARTIAL"
    assert payments[2]["paid_amount"] == 400_000
    assert len(payments[0]["allocations"]) == 2


def test_installment_latest_payment_can_be_undone_from_plan_route(client, session):
    headers = create_user_and_token(client, "installroutesundo", "installroutesundo@example.com", "Password123!")
    _create_installment_budgets(client, headers)
    wallet = _default_wallet(client, headers)
    starting_balance = wallet["current_balance"]
    plan = _create_installment(client, headers)

    paid = client.post(
        f"/installments/{plan['id']}/payments",
        json={
            "amount": 300_000,
            "wallet_allocations": [{"wallet_id": wallet["id"], "amount": 300_000}],
        },
        headers=headers,
    )
    assert paid.status_code == 201, paid.text
    paid_payload = paid.json()
    assert paid_payload["debt"]["remaining_amount"] == 5_100_000
    assert client.get("/wallets", headers=headers).json()[0]["current_balance"] == starting_balance - 300_000

    undone = client.post(f"/installments/{plan['id']}/payments/undo-latest", headers=headers)
    assert undone.status_code == 200, undone.text
    payload = undone.json()
    payments = _sorted_payments(payload["plan"])
    assert payload["debt"]["remaining_amount"] == 5_400_000
    assert payments[0]["status"] == "PENDING"
    assert payments[0]["paid_amount"] == 0
    assert payments[0]["allocations"] == []
    assert client.get("/wallets", headers=headers).json()[0]["current_balance"] == starting_balance

    reversal = (
        session.query(models.DebtLedgerEntry)
        .filter(
            models.DebtLedgerEntry.debt_id == plan["debt_id"],
            models.DebtLedgerEntry.entry_type == models.DebtLedgerEntryType.REVERSAL,
        )
        .first()
    )
    assert reversal is not None
    assert reversal.reverses_entry_id is not None


def test_installment_latest_undo_reopens_multi_row_payment(client):
    headers = create_user_and_token(client, "installroutesundomulti", "installroutesundomulti@example.com", "Password123!")
    _create_installment_budgets(client, headers)
    wallet = _default_wallet(client, headers)
    plan = _create_installment(client, headers)

    paid = client.post(
        f"/installments/{plan['id']}/payments",
        json={
            "amount": 1_000_000,
            "wallet_allocations": [{"wallet_id": wallet["id"], "amount": 1_000_000}],
        },
        headers=headers,
    )
    assert paid.status_code == 201, paid.text
    paid_payments = _sorted_payments(paid.json()["plan"])
    assert [payment["paid_amount"] for payment in paid_payments[:3]] == [450_000, 450_000, 100_000]

    undone = client.post(f"/installments/{plan['id']}/payments/undo-latest", headers=headers)
    assert undone.status_code == 200, undone.text
    payments = _sorted_payments(undone.json()["plan"])
    assert undone.json()["debt"]["remaining_amount"] == 5_400_000
    assert [payment["paid_amount"] for payment in payments[:3]] == [0, 0, 0]
    assert [payment["status"] for payment in payments[:3]] == ["PENDING", "PENDING", "PENDING"]


def test_installment_undo_targets_latest_payment_before_older_payment(client):
    headers = create_user_and_token(client, "installroutesundolatest", "installroutesundolatest@example.com", "Password123!")
    _create_installment_budgets(client, headers)
    wallet = _default_wallet(client, headers)
    plan = _create_installment(client, headers)

    first = client.post(
        f"/installments/{plan['id']}/payments",
        json={
            "amount": 300_000,
            "wallet_allocations": [{"wallet_id": wallet["id"], "amount": 300_000}],
        },
        headers=headers,
    )
    assert first.status_code == 201, first.text
    second = client.post(
        f"/installments/{plan['id']}/payments",
        json={
            "amount": 200_000,
            "wallet_allocations": [{"wallet_id": wallet["id"], "amount": 200_000}],
        },
        headers=headers,
    )
    assert second.status_code == 201, second.text

    undone = client.post(f"/installments/{plan['id']}/payments/undo-latest", headers=headers)
    assert undone.status_code == 200, undone.text
    payments = _sorted_payments(undone.json()["plan"])
    assert payments[0]["paid_amount"] == 300_000
    assert payments[0]["status"] == "PARTIAL"
    assert payments[1]["paid_amount"] == 0
    assert payments[1]["status"] == "PENDING"
    assert undone.json()["debt"]["remaining_amount"] == 5_100_000


def test_installment_latest_undo_restores_charge_component_balance(client):
    headers = create_user_and_token(client, "installroutesundocharge", "installroutesundocharge@example.com", "Password123!")
    _create_installment_budgets(client, headers)
    wallet = _default_wallet(client, headers)
    plan = _create_installment(client, headers, total_price=900_000, months=3, item_name="Sofa")

    charge = client.post(
        f"/installments/{plan['id']}/charges",
        json={"charge_type": "PENALTY", "amount": 50_000, "note": "Late fee"},
        headers=headers,
    )
    assert charge.status_code == 201, charge.text
    assert charge.json()["remaining_amount"] == 950_000

    paid = client.post(
        f"/installments/{plan['id']}/payments",
        json={
            "amount": 50_000,
            "wallet_allocations": [{"wallet_id": wallet["id"], "amount": 50_000}],
        },
        headers=headers,
    )
    assert paid.status_code == 201, paid.text
    assert paid.json()["debt"]["remaining_amount"] == 900_000

    undone = client.post(f"/installments/{plan['id']}/payments/undo-latest", headers=headers)
    assert undone.status_code == 200, undone.text
    payload = undone.json()
    assert payload["debt"]["remaining_amount"] == 950_000
    charge_payment = next(payment for payment in payload["plan"]["payments"] if payment["component_type"] == "CHARGE")
    assert charge_payment["paid_amount"] == 0
    assert charge_payment["status"] == "PENDING"


def test_payment_plan_managed_debt_ledger_reversal_stays_blocked(client):
    headers = create_user_and_token(client, "installroutesdebtblock", "installroutesdebtblock@example.com", "Password123!")
    _create_installment_budgets(client, headers)
    wallet = _default_wallet(client, headers)
    plan = _create_installment(client, headers)

    paid = client.post(
        f"/installments/{plan['id']}/payments",
        json={
            "amount": 300_000,
            "wallet_allocations": [{"wallet_id": wallet["id"], "amount": 300_000}],
        },
        headers=headers,
    )
    assert paid.status_code == 201, paid.text

    details = client.get(f"/installments/{plan['id']}/details", headers=headers)
    assert details.status_code == 200, details.text
    payment_entry = next(item for item in details.json()["debt_activity"] if item["kind"] == "PAYMENT")
    reversed_response = client.post(
        f"/debts/{plan['debt_id']}/ledger/{payment_entry['ledger_entry_id']}/reverse",
        json={"note": "Wrong owner"},
        headers=headers,
    )
    assert reversed_response.status_code == 400
    assert reversed_response.json()["detail"] == "debts.policy.managed_by_payment_plan"


def test_installment_goal_linked_payment_undo_is_blocked(client, session):
    headers = create_user_and_token(client, "installroutesundogoal", "installroutesundogoal@example.com", "Password123!")
    _create_installment_budgets(client, headers)
    wallet = _default_wallet(client, headers)
    plan = _create_installment(client, headers, total_price=500_000, months=5)

    paid = client.post(
        f"/installments/{plan['id']}/payments",
        json={
            "amount": 100_000,
            "date": user_timezone_today().isoformat(),
            "wallet_allocations": [{"wallet_id": wallet["id"], "amount": 100_000}],
        },
        headers=headers,
    )
    assert paid.status_code == 201, paid.text

    user = session.query(models.User).filter_by(email="installroutesundogoal@example.com").first()
    allocation = (
        session.query(models.InstallmentPaymentAllocation)
        .filter(models.InstallmentPaymentAllocation.owner_id == user.id)
        .first()
    )
    assert allocation.debt_transaction_id is not None
    session.add(
        models.Goals(
            owner_id=user.id,
            title="Pay phone plan",
            target_amount=100_000,
            intent=models.GoalIntent.PAY_OBLIGATION,
            status=models.GoalStatus.ACTIVE,
            linked_debt_id=plan["debt_id"],
            linked_installment_plan_id=plan["id"],
            linked_debt_transaction_id=allocation.debt_transaction_id,
        )
    )
    session.commit()

    undone = client.post(f"/installments/{plan['id']}/payments/undo-latest", headers=headers)
    assert undone.status_code == 400
    assert undone.json()["detail"] == "installments.undo.goal_linked_payment"


def test_installment_with_payment_history_cannot_be_deleted(client):
    headers = create_user_and_token(client, "installroutesdelete", "installroutesdelete@example.com", "Password123!")
    _create_installment_budgets(client, headers)
    wallet = _default_wallet(client, headers)
    plan = _create_installment(client, headers)

    paid = client.post(
        f"/installments/{plan['id']}/payments",
        json={
            "amount": 300_000,
            "wallet_allocations": [{"wallet_id": wallet["id"], "amount": 300_000}],
        },
        headers=headers,
    )
    assert paid.status_code == 201, paid.text

    deleted = client.delete(f"/installments/{plan['id']}", headers=headers)
    assert deleted.status_code == 400
    assert deleted.json()["detail"] == "installments.delete.pristine_required"

    details = client.get(f"/installments/{plan['id']}/details", headers=headers)
    assert details.status_code == 200, details.text
    assert details.json()["plan"]["id"] == plan["id"]


def test_pristine_installment_delete_removes_linked_debt(client):
    headers = create_user_and_token(client, "installroutespristinedelete", "installroutespristinedelete@example.com", "Password123!")
    plan = _create_installment(client, headers)

    deleted = client.delete(f"/installments/{plan['id']}", headers=headers)
    assert deleted.status_code == 204, deleted.text

    missing_plan = client.get(f"/installments/{plan['id']}", headers=headers)
    assert missing_plan.status_code == 404
    missing_debt = client.get(f"/debts/{plan['debt_id']}/details", headers=headers)
    assert missing_debt.status_code == 404


def test_pristine_installment_can_update_safe_details(client):
    headers = create_user_and_token(client, "installroutesupdate", "installroutesupdate@example.com", "Password123!")
    plan = _create_installment(client, headers)

    updated = client.patch(
        f"/installments/{plan['id']}",
        json={"item_name": "Laptop", "store_or_bank_name": "Tech Market"},
        headers=headers,
    )
    assert updated.status_code == 200, updated.text
    assert updated.json()["item_name"] == "Laptop"
    assert updated.json()["store_or_bank_name"] == "Tech Market"


def test_pristine_installment_can_update_schedule_setup(client):
    headers = create_user_and_token(client, "installroutesschedule", "installroutesschedule@example.com", "Password123!")
    plan = _create_installment(client, headers, total_price=1_200_000, months=12)

    updated = client.patch(
        f"/installments/{plan['id']}",
        json={
            "total_price": 900_000,
            "months": 3,
            "frequency": "WEEKLY",
            "start_date": "2026-06-01",
        },
        headers=headers,
    )
    assert updated.status_code == 200, updated.text
    payload = updated.json()
    assert payload["total_price"] == 900_000
    assert payload["remaining_amount"] == 900_000
    assert payload["months"] == 3
    assert payload["payment_count"] == 3
    assert payload["frequency"] == "WEEKLY"
    assert payload["regular_payment_amount"] == 300_000
    payments = _sorted_payments(payload)
    assert [payment["amount"] for payment in payments] == [300_000, 300_000, 300_000]
    assert [payment["due_date"] for payment in payments] == ["2026-06-08", "2026-06-15", "2026-06-22"]


def test_archived_installment_cannot_be_updated(client, session):
    headers = create_user_and_token(client, "installroutesarchived", "installroutesarchived@example.com", "Password123!")
    plan = _create_installment(client, headers)
    plan_model = session.query(models.InstallmentPlan).filter_by(id=plan["id"]).first()
    plan_model.status = models.InstallmentStatus.ARCHIVED
    session.commit()

    updated = client.patch(
        f"/installments/{plan['id']}",
        json={"item_name": "Archived edit"},
        headers=headers,
    )
    assert updated.status_code == 400
    assert updated.json()["detail"] == "installments.archived_locked"


def test_installment_with_payment_history_cannot_update_schedule_setup(client):
    headers = create_user_and_token(client, "installroutesupdatespent", "installroutesupdatespent@example.com", "Password123!")
    _create_installment_budgets(client, headers)
    wallet = _default_wallet(client, headers)
    plan = _create_installment(client, headers, total_price=900_000, months=3)

    paid = client.post(
        f"/installments/{plan['id']}/payments",
        json={
            "amount": 300_000,
            "wallet_allocations": [{"wallet_id": wallet["id"], "amount": 300_000}],
        },
        headers=headers,
    )
    assert paid.status_code == 201, paid.text

    updated = client.patch(
        f"/installments/{plan['id']}",
        json={"total_price": 600_000, "months": 2},
        headers=headers,
    )
    assert updated.status_code == 400
    assert updated.json()["detail"] == "installments.update.setup_requires_pristine"


def test_installment_with_linked_goal_cannot_be_deleted(client):
    headers = create_user_and_token(client, "installroutesgoaldelete", "installroutesgoaldelete@example.com", "Password123!")
    _make_premium(client, headers)
    plan = _create_installment(client, headers, total_price=500_000, months=5)

    goal = client.post(
        "/goals/",
        json={
            "title": "Pay phone plan",
            "target_amount": 500_000,
            "intent": "PAY_OBLIGATION",
            "linked_debt_id": plan["debt_id"],
        },
        headers=headers,
    )
    assert goal.status_code == 201, goal.text
    assert goal.json()["linked_installment_plan_id"] == plan["id"]

    deleted = client.delete(f"/installments/{plan['id']}", headers=headers)
    assert deleted.status_code == 400
    assert deleted.json()["detail"] == "installments.delete.pristine_required"


def test_installment_with_charge_or_write_off_history_cannot_update_schedule_setup(client):
    headers = create_user_and_token(client, "installroutesupdateactivity", "installroutesupdateactivity@example.com", "Password123!")
    _create_installment_budgets(client, headers)
    wallet = _default_wallet(client, headers)
    charged_plan = _create_installment(client, headers, total_price=900_000, months=3, item_name="Sofa")

    charge = client.post(
        f"/installments/{charged_plan['id']}/charges",
        json={"charge_type": "PENALTY", "amount": 50_000, "note": "Late fee"},
        headers=headers,
    )
    assert charge.status_code == 201, charge.text

    charged_update = client.patch(
        f"/installments/{charged_plan['id']}",
        json={"total_price": 600_000, "months": 2},
        headers=headers,
    )
    assert charged_update.status_code == 400
    assert charged_update.json()["detail"] == "installments.update.setup_requires_pristine"

    write_off_plan = _create_installment(client, headers, total_price=900_000, months=3, item_name="Laptop")
    partial = client.post(
        f"/installments/{write_off_plan['id']}/payments",
        json={
            "amount": 200_000,
            "wallet_allocations": [{"wallet_id": wallet["id"], "amount": 200_000}],
        },
        headers=headers,
    )
    assert partial.status_code == 201, partial.text
    first_payment = _sorted_payments(partial.json()["plan"])[0]
    write_off = client.post(f"/installments/payments/{first_payment['id']}/write-off", headers=headers)
    assert write_off.status_code == 200, write_off.text

    write_off_update = client.patch(
        f"/installments/{write_off_plan['id']}",
        json={"total_price": 600_000, "months": 2},
        headers=headers,
    )
    assert write_off_update.status_code == 400
    assert write_off_update.json()["detail"] == "installments.update.setup_requires_pristine"


def test_installment_charge_increases_debt_and_can_be_paid_through_schedule(client, session):
    headers = create_user_and_token(client, "installroutes3", "installroutes3@example.com", "Password123!")
    _create_installment_budgets(client, headers)
    wallet = _default_wallet(client, headers)
    plan = _create_installment(
        client,
        headers,
        total_price=900_000,
        months=3,
        item_name="Sofa",
    )

    charge = client.post(
        f"/installments/{plan['id']}/charges",
        json={"charge_type": "PENALTY", "amount": 50_000, "note": "Late fee"},
        headers=headers,
    )
    assert charge.status_code == 201, charge.text

    details = client.get(f"/installments/{plan['id']}/details", headers=headers).json()
    assert details["debt"]["remaining_amount"] == 950_000
    charge_payment = next(
        payment
        for payment in details["plan"]["payments"]
        if payment["amount"] == 50_000 and payment["note"] == "Late fee"
    )
    assert charge_payment["component_type"] == "CHARGE"
    assert charge_payment["debt_charge_id"] is not None
    assert any(item["kind"] == "CHARGE" for item in details["debt_activity"])

    paid = client.post(
        f"/installments/{plan['id']}/payments",
        json={
            "amount": 950_000,
            "wallet_allocations": [{"wallet_id": wallet["id"], "amount": 950_000}],
        },
        headers=headers,
    )
    assert paid.status_code == 201, paid.text
    assert paid.json()["debt"]["remaining_amount"] == 0
    assert paid.json()["plan"]["status"] == "PAID"
    paid_charge_payment = next(
        payment
        for payment in paid.json()["plan"]["payments"]
        if payment["id"] == charge_payment["id"]
    )
    assert paid_charge_payment["paid_amount"] == 50_000
    paid_principal_payment = next(
        payment
        for payment in paid.json()["plan"]["payments"]
        if payment["component_type"] == "PRINCIPAL"
    )

    session.expire_all()
    principal_event = session.query(models.FinancialEvent).filter_by(
        id=paid_principal_payment["allocations"][0]["financial_event_id"]
    ).one()
    charge_event = session.query(models.FinancialEvent).filter_by(
        id=paid_charge_payment["allocations"][0]["financial_event_id"]
    ).one()
    assert principal_event.reference_type == models.ReferenceType.INSTALLMENT_PAYMENT
    assert principal_event.entity_legs[0].category == models.ExpenseCategory.ELECTRONICS
    assert charge_event.reference_type == models.ReferenceType.DEBT_CHARGE
    assert charge_event.entity_legs[0].category == models.ExpenseCategory.DEBT_CHARGES

    ledger_entries = (
        session.query(models.DebtLedgerEntry)
        .filter(models.DebtLedgerEntry.debt_id == plan["debt_id"])
        .all()
    )
    assert sum(int(entry.charge_delta or 0) for entry in ledger_entries) == 0
    assert sum(
        -int(entry.charge_delta or 0)
        for entry in ledger_entries
        if entry.entry_type == models.DebtLedgerEntryType.PAYMENT
    ) == 50_000
    assert sum(
        -int(entry.principal_delta or 0)
        for entry in ledger_entries
        if entry.entry_type == models.DebtLedgerEntryType.PAYMENT
    ) == 900_000


def test_installment_write_off_tracks_written_off_amount_and_can_be_undone(client, session):
    headers = create_user_and_token(client, "installrouteswriteoff", "installrouteswriteoff@example.com", "Password123!")
    _create_installment_budgets(client, headers)
    wallet = _default_wallet(client, headers)
    plan = _create_installment(client, headers, total_price=900_000, months=3)

    partial = client.post(
        f"/installments/{plan['id']}/payments",
        json={
            "amount": 200_000,
            "wallet_allocations": [{"wallet_id": wallet["id"], "amount": 200_000}],
        },
        headers=headers,
    )
    assert partial.status_code == 201, partial.text
    first_payment = _sorted_payments(partial.json()["plan"])[0]
    assert first_payment["status"] == "PARTIAL"
    assert first_payment["paid_amount"] == 200_000

    write_off = client.post(f"/installments/payments/{first_payment['id']}/write-off", headers=headers)
    assert write_off.status_code == 200, write_off.text
    written = write_off.json()
    assert written["status"] == "PAID"
    assert written["paid_amount"] == 200_000
    assert written["written_off_amount"] == 100_000

    details = client.get(f"/installments/{plan['id']}/details", headers=headers)
    assert details.status_code == 200, details.text
    assert details.json()["debt"]["remaining_amount"] == 600_000
    assert any(item["event_subtype"] == "INSTALLMENT_WRITE_OFF" for item in details.json()["debt_activity"])

    ledger_entry = (
        session.query(models.DebtLedgerEntry)
        .filter(
            models.DebtLedgerEntry.debt_id == plan["debt_id"],
            models.DebtLedgerEntry.event_subtype == "INSTALLMENT_WRITE_OFF",
        )
        .first()
    )
    assert ledger_entry is not None
    assert ledger_entry.amount_delta == -100_000
    assert ledger_entry.principal_delta == -100_000
    assert ledger_entry.charge_delta == 0

    undone = client.post(f"/installments/payments/{first_payment['id']}/undo-write-off", headers=headers)
    assert undone.status_code == 200, undone.text
    assert undone.json()["status"] == "PARTIAL"
    assert undone.json()["paid_amount"] == 200_000
    assert undone.json()["written_off_amount"] == 0

    after_undo = client.get(f"/installments/{plan['id']}/details", headers=headers)
    assert after_undo.status_code == 200, after_undo.text
    assert after_undo.json()["debt"]["remaining_amount"] == 700_000


def test_legacy_mark_paid_uses_linked_debt_ledger(client):
    headers = create_user_and_token(client, "installroutes4", "installroutes4@example.com", "Password123!")
    _create_installment_budgets(client, headers)
    wallet = _default_wallet(client, headers)
    plan = _create_installment(client, headers, total_price=900_000, months=3)
    first_payment = _sorted_payments(plan)[0]

    response = client.post(
        f"/installments/payments/{first_payment['id']}/mark-paid",
        json={
            "wallet_allocations": [{"wallet_id": wallet["id"], "amount": 300_000}],
            "note": "Legacy button",
        },
        headers=headers,
    )
    assert response.status_code == 200, response.text
    assert response.json()["status"] == "PAID"
    assert response.json()["paid_amount"] == 300_000
    assert response.json()["debt_ledger_entry_id"] is not None

    details = client.get(f"/installments/{plan['id']}/details", headers=headers).json()
    assert details["debt"]["remaining_amount"] == 600_000
    assert any(item["kind"] == "PAYMENT" for item in details["debt_activity"])
