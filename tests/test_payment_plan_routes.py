
from datetime import date, timedelta

from app import models
from tests.helpers import create_budget, create_user_and_token, user_timezone_today


def _default_wallet(client, headers):
    response = client.get("/wallets", headers=headers)
    assert response.status_code in (200, 201), response.text
    return response.json()[0]


def _create_payment_plan(client, headers, **overrides):
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
    response = client.post("/payment-plans", json=payload, headers=headers)
    assert response.status_code == 201, response.text
    return response.json()


def _create_payment_plan_budgets(client, headers):
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


def test_payment_plan_creation_uses_plan_owned_schedule_and_details(client):
    headers = create_user_and_token(client, "installroutes1", "installroutes1@example.com", "Password123!")

    plan = _create_payment_plan(client, headers)
    assert plan.get("debt_id") is None
    assert plan["remaining_amount"] == 5_400_000
    assert len(plan["payments"]) == 12
    assert {payment["amount"] for payment in plan["payments"]} == {450_000}

    details = client.get(f"/payment-plans/{plan['id']}/details", headers=headers)
    assert details.status_code in (200, 201), details.text


def test_payment_plan_creation_rejects_start_date_before_supported_boundary(client):
    headers = create_user_and_token(client, "installroutesmindate", "installroutesmindate@example.com", "Password123!")

    response = client.post(
        "/payment-plans",
        json={
            "item_name": "Phone",
            "store_or_bank_name": "Phone Store",
            "total_price": 5_400_000,
            "down_payment": 0,
            "months": 12,
            "frequency": "MONTHLY",
            "start_date": "2019-12-31",
            "expense_category": "Electronics",
        },
        headers=headers,
    )

    assert response.status_code == 422
    assert "validation.date_too_early" in response.text


def test_bank_loan_payment_plan_disbursement_creates_plan_owned_cash_flow_event(client, session):
    headers = create_user_and_token(client, "installroutesloan", "installroutesloan@example.com", "Password123!")
    wallet = _default_wallet(client, headers)
    before_balance = wallet["current_balance"]

    plan = _create_payment_plan(
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

    assert plan.get("debt_id") is None
    assert plan["remaining_amount"] == 5_000_000

    refreshed_wallet = client.get("/wallets", headers=headers).json()[0]
    assert refreshed_wallet["current_balance"] == before_balance + 5_000_000

    event = session.query(models.FinancialEvent).filter_by(reference_type=models.ReferenceType.LOAN_DISBURSEMENT).first()
    assert event is not None
    assert event.event_type == models.TransactionType.DEBT_SETTLEMENT

    details = client.get(f"/payment-plans/{plan['id']}/details", headers=headers).json()
    assert "debt" not in details
    assert "debt_activity" not in details
    assert details["plan"]["plan_type"] == "BANK_LOAN"
    assert details["plan_activity"][0]["event_subtype"] == "LOAN_DISBURSEMENT"
    ledger_entry = session.query(models.PaymentPlanLedgerEntry).filter_by(plan_id=plan["id"]).first()
    assert ledger_entry.financial_event_id == event.id


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
        "/payment-plans",
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
    assert response.json()["detail"] == "payment_plans.loan_disbursement_wallet_not_allowed"


def test_payment_plan_type_and_new_frequencies_are_persisted(client):
    headers = create_user_and_token(client, "installroutesfreq", "installroutesfreq@example.com", "Password123!")
    start = user_timezone_today()

    auto_plan = _create_payment_plan(
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

    auto_details = client.get(f"/payment-plans/{auto_plan['id']}/details", headers=headers)
    assert auto_details.status_code in (200, 201), auto_details.text
    # assert auto_details.json()["debt"]["product_kind"] == "CAR_LOAN"

    mortgage_plan = _create_payment_plan(
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
        "/payment-plans",
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
    assert response.json()["detail"] == "payment_plans.validation.real_expense_category_required"


def test_legacy_payment_plan_without_real_category_cannot_post_deprecated_expense(client, session):
    headers = create_user_and_token(client, "installrouteslegacycat", "installrouteslegacycat@example.com", "Password123!")
    user = session.query(models.User).filter_by(email="installrouteslegacycat@example.com").first()
    assert user is not None
    wallet = _default_wallet(client, headers)
    today = user_timezone_today()

    plan = models.PaymentPlan(
        owner_id=user.id,
        item_name="Legacy sofa",
        store_or_bank_name="Old Store",
        plan_type=models.PaymentPlanType.STORE_INSTALLMENT,
        total_price=300_000,
        down_payment=0,
        remaining_amount=300_000,
        months=3,
        payment_count=3,
        frequency=models.PaymentPlanFrequency.MONTHLY,
        monthly_payment_amount=100_000,
        regular_payment_amount=100_000,
        schedule_rule={"source": "LEGACY"},
        status=models.PaymentPlanStatus.ACTIVE,
        start_date=today,
        expense_category=None,
    )
    session.add(plan)
    session.flush()
    session.add(
        models.PaymentPlanPayment(
            owner_id=user.id,
            plan_id=plan.id,
            amount=100_000,
            due_date=today,
            component_type=models.PaymentPlanPaymentComponentType.PRINCIPAL,
            status=models.PaymentPlanPaymentStatus.PENDING,
        )
    )
    session.commit()
    plan_id = plan.id

    response = client.post(
        f"/payment-plans/{plan_id}/payments",
        json={
            "amount": 100_000,
            "wallet_allocations": [{"wallet_id": wallet["id"], "amount": 100_000}],
        },
        headers=headers,
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "payment_plans.validation.real_expense_category_required"
    session.expire_all()
    refreshed_plan = session.query(models.PaymentPlan).filter_by(id=plan_id).one()
    assert refreshed_plan.debt_id is None
    deprecated_legs = (
        session.query(models.EntityLedger)
        .join(models.FinancialEvent, models.FinancialEvent.id == models.EntityLedger.event_id)
        .filter(
            models.FinancialEvent.owner_id == user.id,
            models.EntityLedger.category == models.ExpenseCategory.PAYMENT_PLANS_DEBT,
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
        counterparty_name="Old Store",
        initial_amount=100_000,
        remaining_amount=100_000,
        currency="UZS",
        date=today,
        expected_return_date=today,
        is_money_transferred=False,
        expense_category=None,
    )
    session.add(debt)
    session.flush()
    plan = models.PaymentPlan(
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
        frequency=models.PaymentPlanFrequency.MONTHLY,
        monthly_payment_amount=100_000,
        regular_payment_amount=100_000,
        schedule_rule={"source": "LEGACY"},
        status=models.PaymentPlanStatus.ACTIVE,
        start_date=today,
        expense_category=None,
    )
    session.add(plan)
    session.flush()
    payment = models.PaymentPlanPayment(
        owner_id=user.id,
        plan_id=plan.id,
        amount=100_000,
        due_date=today,
        component_type=models.PaymentPlanPaymentComponentType.PRINCIPAL,
        status=models.PaymentPlanPaymentStatus.PENDING,
    )
    session.add(payment)
    session.commit()
    payment_id = payment.id
    plan_id = plan.id
    debt_id = debt.id

    response = client.post(
        f"/payment-plans/payments/{payment_id}/mark-paid",
        json={"wallet_allocations": [{"wallet_id": wallet["id"], "amount": 100_000}]},
        headers=headers,
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "payment_plans.validation.real_expense_category_required"
    session.expire_all()
    refreshed_plan = session.query(models.PaymentPlan).filter_by(id=plan_id).one()
    refreshed_debt = session.query(models.Debt).filter_by(id=debt_id).one()
    assert refreshed_plan.expense_category is None
    assert refreshed_debt.expense_category is None
    deprecated_legs = (
        session.query(models.EntityLedger)
        .join(models.FinancialEvent, models.FinancialEvent.id == models.EntityLedger.event_id)
        .filter(
            models.FinancialEvent.owner_id == user.id,
            models.EntityLedger.category == models.ExpenseCategory.PAYMENT_PLANS_DEBT,
        )
        .all()
    )
    assert deprecated_legs == []


def test_payment_plan_partial_and_advance_payment_allocates_across_schedule(client, session):
    headers = create_user_and_token(client, "installroutes2", "installroutes2@example.com", "Password123!")
    _create_payment_plan_budgets(client, headers)
    wallet = _default_wallet(client, headers)
    plan = _create_payment_plan(client, headers)

    partial = client.post(
        f"/payment-plans/{plan['id']}/payments",
        json={
            "amount": 300_000,
            "wallet_allocations": [{"wallet_id": wallet["id"], "amount": 300_000}],
            "note": "Paid what I had",
        },
        headers=headers,
    )
    assert partial.status_code == 201, partial.text
    payments_after_partial = _sorted_payments(partial.json()["plan"])
    assert "debt" not in partial.json()
    assert partial.json()["plan"]["remaining_amount"] == 5_100_000
    assert payments_after_partial[0]["status"] == "PARTIAL"
    assert payments_after_partial[0]["paid_amount"] == 300_000
    payment_event = session.query(models.FinancialEvent).filter_by(id=payments_after_partial[0]["event_id"]).first()
    assert payment_event.reference_type == models.ReferenceType.PAYMENT_PLAN_PAYMENT

    advance = client.post(
        f"/payment-plans/{plan['id']}/payments",
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

    assert "debt" not in payload
    assert payload["plan"]["remaining_amount"] == 4_100_000
    assert payments[0]["status"] == "PAID"
    assert payments[0]["paid_amount"] == 450_000
    assert payments[1]["status"] == "PAID"
    assert payments[1]["paid_amount"] == 450_000
    assert payments[2]["status"] == "PARTIAL"
    assert payments[2]["paid_amount"] == 400_000
    assert len(payments[0]["allocations"]) == 2


def test_payment_plan_latest_payment_can_be_undone_from_plan_route(client, session):
    headers = create_user_and_token(client, "installroutesundo", "installroutesundo@example.com", "Password123!")
    _create_payment_plan_budgets(client, headers)
    wallet = _default_wallet(client, headers)
    starting_balance = wallet["current_balance"]
    plan = _create_payment_plan(client, headers)

    paid = client.post(
        f"/payment-plans/{plan['id']}/payments",
        json={
            "amount": 300_000,
            "wallet_allocations": [{"wallet_id": wallet["id"], "amount": 300_000}],
        },
        headers=headers,
    )
    assert paid.status_code == 201, paid.text
    paid_payload = paid.json()
    assert "debt" not in paid_payload
    assert paid_payload["plan"]["remaining_amount"] == 5_100_000
    assert client.get("/wallets", headers=headers).json()[0]["current_balance"] == starting_balance - 300_000

    undone = client.post(f"/payment-plans/{plan['id']}/payments/undo-latest", headers=headers)
    assert undone.status_code in (200, 201), undone.text
    payload = undone.json()
    payments = _sorted_payments(payload["plan"])
    assert "debt" not in payload
    assert payload["plan"]["remaining_amount"] == 5_400_000
    assert payments[0]["status"] == "PENDING"
    assert payments[0]["paid_amount"] == 0
    assert payments[0]["allocations"] == []
    assert client.get("/wallets", headers=headers).json()[0]["current_balance"] == starting_balance

    reversal = (
        session.query(models.PaymentPlanLedgerEntry)
        .filter(
            models.PaymentPlanLedgerEntry.plan_id == plan["id"],
            models.PaymentPlanLedgerEntry.entry_type == models.PaymentPlanLedgerEntryType.REVERSAL,
        )
        .first()
    )
    assert reversal is not None
    assert reversal.reverses_entry_id is not None


def test_payment_plan_latest_undo_reopens_multi_row_payment(client):
    headers = create_user_and_token(client, "installroutesundomulti", "installroutesundomulti@example.com", "Password123!")
    _create_payment_plan_budgets(client, headers)
    wallet = _default_wallet(client, headers)
    plan = _create_payment_plan(client, headers)

    paid = client.post(
        f"/payment-plans/{plan['id']}/payments",
        json={
            "amount": 1_000_000,
            "wallet_allocations": [{"wallet_id": wallet["id"], "amount": 1_000_000}],
        },
        headers=headers,
    )
    assert paid.status_code == 201, paid.text
    paid_payments = _sorted_payments(paid.json()["plan"])
    assert [payment["paid_amount"] for payment in paid_payments[:3]] == [450_000, 450_000, 100_000]

    undone = client.post(f"/payment-plans/{plan['id']}/payments/undo-latest", headers=headers)
    assert undone.status_code in (200, 201), undone.text
    payments = _sorted_payments(undone.json()["plan"])
    assert "debt" not in undone.json()
    assert undone.json()["plan"]["remaining_amount"] == 5_400_000
    assert [payment["paid_amount"] for payment in payments[:3]] == [0, 0, 0]
    assert [payment["status"] for payment in payments[:3]] == ["PENDING", "PENDING", "PENDING"]


def test_payment_plan_undo_targets_latest_payment_before_older_payment(client):
    headers = create_user_and_token(client, "installroutesundolatest", "installroutesundolatest@example.com", "Password123!")
    _create_payment_plan_budgets(client, headers)
    wallet = _default_wallet(client, headers)
    plan = _create_payment_plan(client, headers)

    first = client.post(
        f"/payment-plans/{plan['id']}/payments",
        json={
            "amount": 300_000,
            "wallet_allocations": [{"wallet_id": wallet["id"], "amount": 300_000}],
        },
        headers=headers,
    )
    assert first.status_code == 201, first.text
    second = client.post(
        f"/payment-plans/{plan['id']}/payments",
        json={
            "amount": 200_000,
            "wallet_allocations": [{"wallet_id": wallet["id"], "amount": 200_000}],
        },
        headers=headers,
    )
    assert second.status_code == 201, second.text

    undone = client.post(f"/payment-plans/{plan['id']}/payments/undo-latest", headers=headers)
    assert undone.status_code in (200, 201), undone.text
    payments = _sorted_payments(undone.json()["plan"])
    assert payments[0]["paid_amount"] == 300_000
    assert payments[0]["status"] == "PARTIAL"
    assert payments[1]["paid_amount"] == 0
    assert payments[1]["status"] == "PENDING"
    assert "debt" not in undone.json()
    assert undone.json()["plan"]["remaining_amount"] == 5_100_000


def test_payment_plan_latest_undo_restores_charge_component_balance(client):
    headers = create_user_and_token(client, "installroutesundocharge", "installroutesundocharge@example.com", "Password123!")
    _create_payment_plan_budgets(client, headers)
    wallet = _default_wallet(client, headers)
    plan = _create_payment_plan(client, headers, total_price=900_000, months=3, item_name="Sofa")

    charge = client.post(
        f"/payment-plans/{plan['id']}/charges",
        json={"charge_type": "PENALTY", "amount": 50_000, "note": "Late fee"},
        headers=headers,
    )
    assert charge.status_code == 201, charge.text
    assert charge.json()["remaining_amount"] == 950_000

    paid = client.post(
        f"/payment-plans/{plan['id']}/payments",
        json={
            "amount": 50_000,
            "wallet_allocations": [{"wallet_id": wallet["id"], "amount": 50_000}],
        },
        headers=headers,
    )
    assert paid.status_code == 201, paid.text
    assert "debt" not in paid.json()
    assert paid.json()["plan"]["remaining_amount"] == 900_000

    undone = client.post(f"/payment-plans/{plan['id']}/payments/undo-latest", headers=headers)
    assert undone.status_code in (200, 201), undone.text
    payload = undone.json()
    assert "debt" not in payload
    assert payload["plan"]["remaining_amount"] == 950_000
    charge_payment = next(payment for payment in payload["plan"]["payments"] if payment["component_type"] == "CHARGE")
    assert charge_payment["paid_amount"] == 0
    assert charge_payment["status"] == "PENDING"


def test_payment_plan_payment_activity_is_plan_owned_not_debt_owned(client):
    headers = create_user_and_token(client, "installroutesdebtblock", "installroutesdebtblock@example.com", "Password123!")
    _create_payment_plan_budgets(client, headers)
    wallet = _default_wallet(client, headers)
    plan = _create_payment_plan(client, headers)

    paid = client.post(
        f"/payment-plans/{plan['id']}/payments",
        json={
            "amount": 300_000,
            "wallet_allocations": [{"wallet_id": wallet["id"], "amount": 300_000}],
        },
        headers=headers,
    )
    assert paid.status_code == 201, paid.text

    details = client.get(f"/payment-plans/{plan['id']}/details", headers=headers)
    assert details.status_code in (200, 201), details.text
    payload = details.json()
    assert "debt" not in payload
    assert "debt_activity" not in payload
    assert any(item["entry_type"] == "PAYMENT" for item in payload["plan_activity"])


# def test_payment_plan_goal_linked_payment_undo_is_blocked(client, session):
#     headers = create_user_and_token(client, "installroutesundogoal", "installroutesundogoal@example.com", "Password123!")
#     _create_payment_plan_budgets(client, headers)
#     wallet = _default_wallet(client, headers)
#     plan = _create_payment_plan(client, headers, total_price=500_000, months=5)
# 
#     paid = client.post(
#         f"/payment-plans/{plan['id']}/payments",
#         json={
#             "amount": 100_000,
#             "date": user_timezone_today().isoformat(),
#             "wallet_allocations": [{"wallet_id": wallet["id"], "amount": 100_000}],
#         },
#         headers=headers,
#     )
#     assert paid.status_code == 201, paid.text
# 
#     user = session.query(models.User).filter_by(email="installroutesundogoal@example.com").first()
#     allocation = (
#         session.query(models.PaymentPlanPaymentAllocation)
#         .filter(models.PaymentPlanPaymentAllocation.owner_id == user.id)
#         .first()
#     )
#     assert allocation.debt_transaction_id is not None
#     session.add(
#         models.Goals(
#             owner_id=user.id,
#             title="Pay phone plan",
#             target_amount=100_000,
#             intent=models.GoalIntent.PAY_OBLIGATION,
#             status=models.GoalStatus.ACTIVE,
#             linked_debt_id=plan["debt_id"],
#             linked_payment_plan_id=plan["id"],
#             linked_debt_transaction_id=allocation.debt_transaction_id,
#         )
#     )
#     session.commit()
# 
#     undone = client.post(f"/payment-plans/{plan['id']}/payments/undo-latest", headers=headers)
#     assert undone.status_code == 400
#     assert undone.json()["detail"] == "payment_plans.undo.goal_linked_payment"


def test_payment_plan_with_payment_history_cannot_be_deleted(client):
    headers = create_user_and_token(client, "installroutesdelete", "installroutesdelete@example.com", "Password123!")
    _create_payment_plan_budgets(client, headers)
    wallet = _default_wallet(client, headers)
    plan = _create_payment_plan(client, headers)

    paid = client.post(
        f"/payment-plans/{plan['id']}/payments",
        json={
            "amount": 300_000,
            "wallet_allocations": [{"wallet_id": wallet["id"], "amount": 300_000}],
        },
        headers=headers,
    )
    assert paid.status_code == 201, paid.text

    deleted = client.delete(f"/payment-plans/{plan['id']}", headers=headers)
    assert deleted.status_code == 400
    assert deleted.json()["detail"] == "payment_plans.delete.pristine_required"

    details = client.get(f"/payment-plans/{plan['id']}/details", headers=headers)
    assert details.status_code in (200, 201), details.text
    assert details.json()["plan"]["id"] == plan["id"]


def test_pristine_payment_plan_delete_succeeds(client):
    headers = create_user_and_token(client, "installroutespristinedelete", "installroutespristinedelete@example.com", "Password123!")
    plan = _create_payment_plan(client, headers)

    deleted = client.delete(f"/payment-plans/{plan['id']}", headers=headers)
    assert deleted.status_code == 204, deleted.text

    missing_plan = client.get(f"/payment-plans/{plan['id']}", headers=headers)
    assert missing_plan.status_code == 404


def test_pristine_payment_plan_delete_does_not_touch_legacy_linked_debt(client, session):
    headers = create_user_and_token(client, "installroutesdeletelegacy", "installroutesdeletelegacy@example.com", "Password123!")
    plan = _create_payment_plan(client, headers)
    user = session.query(models.User).filter_by(email="installroutesdeletelegacy@example.com").one()
    debt = models.Debt(
        owner_id=user.id,
        debt_type=models.DebtType.OWING,
        origin_kind=models.DebtOriginKind.FINANCED_ASSET_PURCHASE,
        counterparty_kind=models.DebtCounterpartyKind.STORE,
        counterparty_name="Legacy Store",
        initial_amount=5_400_000,
        remaining_amount=5_400_000,
        currency="UZS",
        date=user_timezone_today(),
        expected_return_date=user_timezone_today(),
        is_money_transferred=False,
        expense_category=models.ExpenseCategory.ELECTRONICS,
    )
    session.add(debt)
    session.flush()
    plan_model = session.query(models.PaymentPlan).filter_by(id=plan["id"]).one()
    plan_model.debt_id = debt.id
    session.commit()

    deleted = client.delete(f"/payment-plans/{plan['id']}", headers=headers)

    assert deleted.status_code == 204, deleted.text
    session.expire_all()
    assert session.query(models.PaymentPlan).filter_by(id=plan["id"]).first() is None
    assert session.query(models.Debt).filter_by(id=debt.id).one().remaining_amount == 5_400_000


def test_pristine_payment_plan_can_update_safe_details(client):
    headers = create_user_and_token(client, "installroutesupdate", "installroutesupdate@example.com", "Password123!")
    plan = _create_payment_plan(client, headers)

    updated = client.patch(
        f"/payment-plans/{plan['id']}",
        json={"item_name": "Laptop", "store_or_bank_name": "Tech Market"},
        headers=headers,
    )
    assert updated.status_code in (200, 201), updated.text
    assert updated.json()["item_name"] == "Laptop"
    assert updated.json()["store_or_bank_name"] == "Tech Market"


def test_payment_plan_safe_metadata_can_update_after_activity(client):
    headers = create_user_and_token(client, "installroutesupdatemeta", "installroutesupdatemeta@example.com", "Password123!")
    _create_payment_plan_budgets(client, headers)
    wallet = _default_wallet(client, headers)
    plan = _create_payment_plan(client, headers, total_price=900_000, months=3)

    paid = client.post(
        f"/payment-plans/{plan['id']}/payments",
        json={
            "amount": 300_000,
            "wallet_allocations": [{"wallet_id": wallet["id"], "amount": 300_000}],
        },
        headers=headers,
    )
    assert paid.status_code == 201, paid.text

    updated = client.patch(
        f"/payment-plans/{plan['id']}",
        json={
            "item_name": "Work laptop",
            "store_or_bank_name": "Updated Store",
            "expense_category": "Business / Work",
        },
        headers=headers,
    )

    assert updated.status_code in (200, 201), updated.text
    assert updated.json()["item_name"] == "Work laptop"
    assert updated.json()["store_or_bank_name"] == "Updated Store"
    assert updated.json()["expense_category"] == "Business / Work"
    assert updated.json()["remaining_amount"] == 600_000


def test_pristine_payment_plan_can_update_schedule_setup(client):
    headers = create_user_and_token(client, "installroutesschedule", "installroutesschedule@example.com", "Password123!")
    plan = _create_payment_plan(client, headers, total_price=1_200_000, months=12)

    updated = client.patch(
        f"/payment-plans/{plan['id']}",
        json={
            "total_price": 900_000,
            "down_payment": 300_000,
            "months": 3,
            "frequency": "WEEKLY",
            "start_date": "2026-06-01",
        },
        headers=headers,
    )
    assert updated.status_code in (200, 201), updated.text
    payload = updated.json()
    assert payload["total_price"] == 900_000
    assert payload["down_payment"] == 300_000
    assert payload["remaining_amount"] == 600_000
    assert payload["months"] == 3
    assert payload["payment_count"] == 3
    assert payload["frequency"] == "WEEKLY"
    assert payload["regular_payment_amount"] == 200_000
    payments = _sorted_payments(payload)
    assert [payment["amount"] for payment in payments] == [200_000, 200_000, 200_000]
    assert [payment["due_date"] for payment in payments] == ["2026-06-08", "2026-06-15", "2026-06-22"]


def test_archived_payment_plan_cannot_be_updated(client, session):
    headers = create_user_and_token(client, "installroutesarchived", "installroutesarchived@example.com", "Password123!")
    plan = _create_payment_plan(client, headers)
    plan_model = session.query(models.PaymentPlan).filter_by(id=plan["id"]).first()
    plan_model.status = models.PaymentPlanStatus.ARCHIVED
    session.commit()

    updated = client.patch(
        f"/payment-plans/{plan['id']}",
        json={"item_name": "Archived edit"},
        headers=headers,
    )
    assert updated.status_code == 400
    assert updated.json()["detail"] == "payment_plans.archived_locked"


def test_payment_plan_with_payment_history_cannot_update_schedule_setup(client):
    headers = create_user_and_token(client, "installroutesupdatespent", "installroutesupdatespent@example.com", "Password123!")
    _create_payment_plan_budgets(client, headers)
    wallet = _default_wallet(client, headers)
    plan = _create_payment_plan(client, headers, total_price=900_000, months=3)

    paid = client.post(
        f"/payment-plans/{plan['id']}/payments",
        json={
            "amount": 300_000,
            "wallet_allocations": [{"wallet_id": wallet["id"], "amount": 300_000}],
        },
        headers=headers,
    )
    assert paid.status_code == 201, paid.text

    updated = client.patch(
        f"/payment-plans/{plan['id']}",
        json={"total_price": 600_000, "months": 2},
        headers=headers,
    )
    assert updated.status_code == 400
    assert updated.json()["detail"] == "payment_plans.update.setup_requires_pristine"


# def test_payment_plan_with_linked_goal_cannot_be_deleted(client):
#     headers = create_user_and_token(client, "installroutesgoaldelete", "installroutesgoaldelete@example.com", "Password123!")
#     _make_premium(client, headers)
#     plan = _create_payment_plan(client, headers, total_price=500_000, months=5)
# 
#     goal = client.post(
#         "/goals/",
#         json={
#             "title": "Pay phone plan",
#             "target_amount": 500_000,
#             "intent": "PAY_OBLIGATION",
#             "linked_debt_id": plan["debt_id"],
#         },
#         headers=headers,
#     )
#     assert goal.status_code == 201, goal.text
#     assert goal.json()["linked_payment_plan_id"] == plan["id"]
# 
#     deleted = client.delete(f"/payment-plans/{plan['id']}", headers=headers)
#     assert deleted.status_code == 400
#     assert deleted.json()["detail"] == "payment_plans.delete.pristine_required"
# 
# 
# def test_payment_plan_with_charge_or_write_off_history_cannot_update_schedule_setup(client):
#     headers = create_user_and_token(client, "installroutesupdateactivity", "installroutesupdateactivity@example.com", "Password123!")
    _create_payment_plan_budgets(client, headers)
    wallet = _default_wallet(client, headers)
    charged_plan = _create_payment_plan(client, headers, total_price=900_000, months=3, item_name="Sofa")

    charge = client.post(
        f"/payment-plans/{charged_plan['id']}/charges",
        json={"charge_type": "PENALTY", "amount": 50_000, "note": "Late fee"},
        headers=headers,
    )
    assert charge.status_code == 201, charge.text

    charged_update = client.patch(
        f"/payment-plans/{charged_plan['id']}",
        json={"total_price": 600_000, "months": 2},
        headers=headers,
    )
    assert charged_update.status_code == 400
    assert charged_update.json()["detail"] == "payment_plans.update.setup_requires_pristine"

    write_off_plan = _create_payment_plan(client, headers, total_price=900_000, months=3, item_name="Laptop")
    partial = client.post(
        f"/payment-plans/{write_off_plan['id']}/payments",
        json={
            "amount": 200_000,
            "wallet_allocations": [{"wallet_id": wallet["id"], "amount": 200_000}],
        },
        headers=headers,
    )
    assert partial.status_code == 201, partial.text
    first_payment = _sorted_payments(partial.json()["plan"])[0]
    write_off = client.post(f"/payment-plans/payments/{first_payment['id']}/write-off", headers=headers)
    assert write_off.status_code in (200, 201), write_off.text

    write_off_update = client.patch(
        f"/payment-plans/{write_off_plan['id']}",
        json={"total_price": 600_000, "months": 2},
        headers=headers,
    )
    assert write_off_update.status_code == 400
    assert write_off_update.json()["detail"] == "payment_plans.update.setup_requires_pristine"


def test_payment_plan_charge_increases_debt_and_can_be_paid_through_schedule(client, session):
    headers = create_user_and_token(client, "installroutes3", "installroutes3@example.com", "Password123!")
    _create_payment_plan_budgets(client, headers)
    wallet = _default_wallet(client, headers)
    plan = _create_payment_plan(
        client,
        headers,
        total_price=900_000,
        months=3,
        item_name="Sofa",
    )

    charge = client.post(
        f"/payment-plans/{plan['id']}/charges",
        json={"charge_type": "PENALTY", "amount": 50_000, "note": "Late fee"},
        headers=headers,
    )
    assert charge.status_code == 201, charge.text

    details = client.get(f"/payment-plans/{plan['id']}/details", headers=headers).json()
    assert details["plan"]["remaining_amount"] == 950_000
    charge_payment = next(
        payment
        for payment in details["plan"]["payments"]
        if payment["amount"] == 50_000 and payment["note"] == "Late fee"
    )
    assert charge_payment["component_type"] == "CHARGE"
    assert charge_payment["payment_plan_charge_id"] is not None
    assert any(item["entry_type"] == "CHARGE" for item in details["plan_activity"])

    paid = client.post(
        f"/payment-plans/{plan['id']}/payments",
        json={
            "amount": 950_000,
            "wallet_allocations": [{"wallet_id": wallet["id"], "amount": 950_000}],
        },
        headers=headers,
    )
    assert paid.status_code == 201, paid.text
    assert "debt" not in paid.json()
    assert paid.json()["plan"]["remaining_amount"] == 0
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
    assert principal_event.reference_type == models.ReferenceType.PAYMENT_PLAN_PAYMENT
    assert principal_event.entity_legs[0].category == models.ExpenseCategory.ELECTRONICS
    assert charge_event.reference_type == models.ReferenceType.PAYMENT_PLAN_FEE
    assert charge_event.entity_legs[0].category == models.ExpenseCategory.DEBT_CHARGES

    ledger_entries = (
        session.query(models.PaymentPlanLedgerEntry)
        .filter(models.PaymentPlanLedgerEntry.plan_id == plan["id"])
        .all()
    )
    assert sum(int(entry.charge_delta or 0) for entry in ledger_entries) == 0
    assert sum(
        -int(entry.charge_delta or 0)
        for entry in ledger_entries
        if entry.entry_type == models.PaymentPlanLedgerEntryType.PAYMENT
    ) == 50_000
    assert sum(
        -int(entry.principal_delta or 0)
        for entry in ledger_entries
        if entry.entry_type == models.PaymentPlanLedgerEntryType.PAYMENT
    ) == 900_000


def test_payment_plan_write_off_tracks_written_off_amount_and_can_be_undone(client, session):
    headers = create_user_and_token(client, "installrouteswriteoff", "installrouteswriteoff@example.com", "Password123!")
    _create_payment_plan_budgets(client, headers)
    wallet = _default_wallet(client, headers)
    plan = _create_payment_plan(client, headers, total_price=900_000, months=3)

    partial = client.post(
        f"/payment-plans/{plan['id']}/payments",
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

    write_off = client.post(f"/payment-plans/payments/{first_payment['id']}/write-off", headers=headers)
    assert write_off.status_code in (200, 201), write_off.text
    written = write_off.json()
    assert written["status"] == "PAID"
    assert written["paid_amount"] == 200_000
    assert written["written_off_amount"] == 100_000

    details = client.get(f"/payment-plans/{plan['id']}/details", headers=headers)
    assert details.status_code in (200, 201), details.text
    assert details.json()["plan"]["remaining_amount"] == 600_000
    assert any(item["event_subtype"] == "PAYMENT_PLAN_WRITE_OFF" for item in details.json()["plan_activity"])

    ledger_entry = (
        session.query(models.PaymentPlanLedgerEntry)
        .filter(
            models.PaymentPlanLedgerEntry.plan_id == plan["id"],
            models.PaymentPlanLedgerEntry.entry_type == models.PaymentPlanLedgerEntryType.ADJUSTMENT,
            models.PaymentPlanLedgerEntry.event_subtype == "PAYMENT_PLAN_WRITE_OFF",
        )
        .first()
    )
    assert ledger_entry is not None
    assert ledger_entry.amount_delta == -100_000
    assert ledger_entry.principal_delta == -100_000
    assert ledger_entry.charge_delta == 0

    undone = client.post(f"/payment-plans/payments/{first_payment['id']}/undo-write-off", headers=headers)
    assert undone.status_code in (200, 201), undone.text
    assert undone.json()["status"] == "PARTIAL"
    assert undone.json()["paid_amount"] == 200_000
    assert undone.json()["written_off_amount"] == 0

    after_undo = client.get(f"/payment-plans/{plan['id']}/details", headers=headers)
    assert after_undo.status_code in (200, 201), after_undo.text
    assert after_undo.json()["plan"]["remaining_amount"] == 700_000


def test_legacy_mark_paid_uses_plan_owned_ledger(client):
    headers = create_user_and_token(client, "installroutes4", "installroutes4@example.com", "Password123!")
    _create_payment_plan_budgets(client, headers)
    wallet = _default_wallet(client, headers)
    plan = _create_payment_plan(client, headers, total_price=900_000, months=3)
    first_payment = _sorted_payments(plan)[0]

    response = client.post(
        f"/payment-plans/payments/{first_payment['id']}/mark-paid",
        json={
            "wallet_allocations": [{"wallet_id": wallet["id"], "amount": 300_000}],
            "note": "Legacy button",
        },
        headers=headers,
    )
    assert response.status_code in (200, 201), response.text
    assert response.json()["status"] == "PAID"
    assert response.json()["paid_amount"] == 300_000
    assert response.json()["payment_plan_ledger_entry_id"] is not None

    details = client.get(f"/payment-plans/{plan['id']}/details", headers=headers).json()
    assert details["plan"]["remaining_amount"] == 600_000
    # assert any(item["entry_type"] == "PAYMENT" for item in details["plan_activity"])
