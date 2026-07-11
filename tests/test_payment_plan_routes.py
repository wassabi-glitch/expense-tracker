
from datetime import date, timedelta

from app import models
from tests.helpers import (
    create_budget,
    create_user_and_token,
    TEST_TIMEZONE,
    user_timezone_today,
)


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
            models.PaymentPlanLedgerEntry.entry_type == models.PaymentPlanLedgerEntryType.WRITE_OFF,
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


# ---------------------------------------------------------------------------
# Ticket 7: Schedule Model Foundation & Flat-Total Preview
# ---------------------------------------------------------------------------


def test_flat_total_schedule_preview_generates_correct_rows(client):
    """Preview a flat-total schedule and verify row count, amounts, and totals."""
    headers = create_user_and_token(client, "previewflat1", "previewflat1@example.com", "Password123!")
    start = user_timezone_today()
    response = client.post(
        "/payment-plans/preview",
        json={
            "plan_type": "STORE_INSTALLMENT",
            "total_price": 12_000_000,
            "down_payment": 3_000_000,
            "payment_count": 12,
            "frequency": "MONTHLY",
            "first_due_date": start.isoformat(),
        },
        headers=headers,
    )
    assert response.status_code == 200, response.text
    data = response.json()

    assert data["schedule_model"] == "FLAT_TOTAL"
    assert data["total_principal"] == 9_000_000
    assert data["total_charges"] == 0
    assert data["total_to_pay"] == 9_000_000
    assert data["payment_count"] == 12
    assert data["frequency"] == "MONTHLY"
    assert len(data["rows"]) == 12
    # First 11 rows should all be base_payment (750,000), last row gets remainder
    base = 9_000_000 // 12  # 750,000
    for i, row in enumerate(data["rows"]):
        assert row["component_type"] == "PRINCIPAL"
        if i < 11:
            assert row["amount"] == base, f"Row {i}: expected {base}, got {row['amount']}"
        else:
            expected_last = base + (9_000_000 % 12)  # 750,000
            assert row["amount"] == expected_last, f"Last row: expected {expected_last}, got {row['amount']}"


def test_flat_total_preview_rejects_missing_total_price(client):
    """Preview without total_price returns 400."""
    headers = create_user_and_token(client, "previewflat2", "previewflat2@example.com", "Password123!")
    start = user_timezone_today()
    response = client.post(
        "/payment-plans/preview",
        json={
            "plan_type": "STORE_INSTALLMENT",
            "payment_count": 6,
            "frequency": "MONTHLY",
            "first_due_date": start.isoformat(),
        },
        headers=headers,
    )
    assert response.status_code == 400, response.text


def test_flat_total_creation_stores_schedule_model(client):
    """Creating a store installment plan stores FLAT_TOTAL schedule_model."""
    headers = create_user_and_token(client, "createflat1", "createflat1@example.com", "Password123!")
    _create_payment_plan_budgets(client, headers)
    start = user_timezone_today()
    plan = _create_payment_plan(
        client,
        headers,
        item_name="Test Flat Plan",
        plan_type="STORE_INSTALLMENT",
        total_price=6_000_000,
        down_payment=1_000_000,
        months=6,
        frequency="MONTHLY",
        start_date=start.isoformat(),
        expense_category="Electronics",
    )
    assert plan["schedule_model"] == "FLAT_TOTAL"
    assert plan["schedule_rule"]["source"] == "FLAT_TOTAL"
    # Verify payment count
    assert plan["payment_count"] == 6
    assert len(plan["payments"]) == 6
    # All rows should be PRINCIPAL
    for p in plan["payments"]:
        assert p["component_type"] == "PRINCIPAL"


def test_product_financing_defaults_to_flat_total(client):
    """PRODUCT_FINANCING plan type defaults to FLAT_TOTAL schedule model."""
    headers = create_user_and_token(client, "newtest1", "newtest1@example.com", "Password123!")
    _create_payment_plan_budgets(client, headers)
    start = user_timezone_today()
    plan = _create_payment_plan(
        client,
        headers,
        item_name="Laptop Financing",
        plan_type="PRODUCT_FINANCING",
        total_price=8_000_000,
        down_payment=0,
        months=4,
        frequency="MONTHLY",
        start_date=start.isoformat(),
        expense_category="Electronics",
    )
    assert plan["schedule_model"] == "FLAT_TOTAL"


def test_flat_total_zero_remaining_creates_paid_plan(client):
    """Flat plan with down_payment >= total_price creates PAID status with no rows."""
    headers = create_user_and_token(client, "newtest2", "newtest2@example.com", "Password123!")
    start = user_timezone_today()
    # Create a budget large enough
    create_budget(
        client, headers,
        category="Electronics",
        monthly_limit=10_000_000,
        budget_year=start.year,
        budget_month=start.month,
    )
    plan = _create_payment_plan(
        client,
        headers,
        item_name="Fully Paid",
        plan_type="STORE_INSTALLMENT",
        total_price=1_000_000,
        down_payment=1_000_000,
        months=1,
        frequency="MONTHLY",
        start_date=start.isoformat(),
        expense_category="Electronics",
    )
    assert plan["remaining_amount"] == 0
    assert len(plan["payments"]) == 0


# ---------------------------------------------------------------------------
# Ticket 8: Amortized Loan Schedules & Installment Grouping
# ---------------------------------------------------------------------------


def test_amortized_schedule_preview_generates_both_component_types(client):
    """Preview an amortized loan schedule. Should produce CHARGE and PRINCIPAL rows."""
    headers = create_user_and_token(client, "newtest3", "newtest3@example.com", "Password123!")
    start = user_timezone_today()
    response = client.post(
        "/payment-plans/preview",
        json={
            "plan_type": "BANK_LOAN",
            "schedule_model": "AMORTIZED_LOAN",
            "principal": 4_070_000,
            "annual_interest_rate": 19.9,
            "payment_count": 3,
            "frequency": "MONTHLY",
            "first_due_date": start.isoformat(),
        },
        headers=headers,
    )
    assert response.status_code == 200, response.text
    data = response.json()

    assert data["schedule_model"] == "AMORTIZED_LOAN"
    # Should have CHARGE and PRINCIPAL rows
    charge_rows = [r for r in data["rows"] if r["component_type"] == "CHARGE"]
    principal_rows = [r for r in data["rows"] if r["component_type"] == "PRINCIPAL"]
    assert len(charge_rows) == 3
    assert len(principal_rows) == 3
    assert data["total_charges"] > 0
    assert data["total_principal"] == 4_070_000
    # Total must match ADR 0028 example (within rounding)
    assert abs(data["total_to_pay"] - 4_205_728) < 10


def test_amortized_rows_have_installment_grouping(client):
    """Amortized schedule rows should have installment_number grouping CHARGE+PRINCIPAL."""
    headers = create_user_and_token(client, "newtest4", "newtest4@example.com", "Password123!")
    start = user_timezone_today()
    response = client.post(
        "/payment-plans/preview",
        json={
            "plan_type": "BANK_LOAN",
            "schedule_model": "AMORTIZED_LOAN",
            "principal": 4_070_000,
            "annual_interest_rate": 19.9,
            "payment_count": 3,
            "frequency": "MONTHLY",
            "first_due_date": start.isoformat(),
        },
        headers=headers,
    )
    assert response.status_code == 200, response.text
    data = response.json()

    # Each installment should have exactly two rows: CHARGE then PRINCIPAL
    installment_numbers = [r["installment_number"] for r in data["rows"]]
    assert installment_numbers == [1, 1, 2, 2, 3, 3]

    # Check grouping by installment
    for inst_num in [1, 2, 3]:
        inst_rows = [r for r in data["rows"] if r["installment_number"] == inst_num]
        assert len(inst_rows) == 2, f"Installment {inst_num}: expected 2 rows, got {len(inst_rows)}"
        assert inst_rows[0]["component_type"] == "CHARGE"
        assert inst_rows[1]["component_type"] == "PRINCIPAL"
        # Same due date within installment
        assert inst_rows[0]["due_date"] == inst_rows[1]["due_date"]


def test_amortized_schedule_preview_rejects_missing_principal(client):
    """Amortized preview without principal returns 400."""
    headers = create_user_and_token(client, "newtest5", "newtest5@example.com", "Password123!")
    start = user_timezone_today()
    response = client.post(
        "/payment-plans/preview",
        json={
            "plan_type": "BANK_LOAN",
            "schedule_model": "AMORTIZED_LOAN",
            "annual_interest_rate": 19.9,
            "payment_count": 3,
            "frequency": "MONTHLY",
            "first_due_date": start.isoformat(),
        },
        headers=headers,
    )
    assert response.status_code == 400, response.text


def test_amortized_schedule_preview_rejects_missing_rate(client):
    """Amortized preview without annual_interest_rate returns 400."""
    headers = create_user_and_token(client, "newtest6", "newtest6@example.com", "Password123!")
    start = user_timezone_today()
    response = client.post(
        "/payment-plans/preview",
        json={
            "plan_type": "BANK_LOAN",
            "schedule_model": "AMORTIZED_LOAN",
            "principal": 4_070_000,
            "payment_count": 3,
            "frequency": "MONTHLY",
            "first_due_date": start.isoformat(),
        },
        headers=headers,
    )
    assert response.status_code == 400, response.text


def test_amortized_creation_stores_schedule_model_and_metadata(client):
    """Creating a bank loan plan with interest stores AMORTIZED_LOAN and metadata."""
    headers = create_user_and_token(client, "newtest7", "newtest7@example.com", "Password123!")
    _create_payment_plan_budgets(client, headers)
    start = user_timezone_today()
    plan = _create_payment_plan(
        client,
        headers,
        item_name="Car Loan",
        store_or_bank_name="AutoBank",
        plan_type="BANK_LOAN",
        total_price=4_070_000,  # principal
        down_payment=0,
        months=3,
        frequency="MONTHLY",
        start_date=start.isoformat(),
        expense_category="Transport",
        annual_interest_rate=19.9,
    )
    assert plan["schedule_model"] == "AMORTIZED_LOAN"
    assert plan["schedule_rule"]["source"] == "AMORTIZED_LOAN"
    assert plan["generation_metadata"] is not None
    assert plan["generation_metadata"]["principal"] == 4_070_000

    # Should have both CHARGE and PRINCIPAL rows
    payments = plan["payments"]
    charge_rows = [p for p in payments if p["component_type"] == "CHARGE"]
    principal_rows = [p for p in payments if p["component_type"] == "PRINCIPAL"]
    assert len(charge_rows) == 3
    assert len(principal_rows) == 3

    # Installment grouping
    for p in charge_rows + principal_rows:
        assert p["installment_number"] is not None


def test_amortized_zero_rate_falls_back_to_flat_total(client):
    """Bank loan without interest rate falls back to flat-total behavior."""
    headers = create_user_and_token(client, "newtest8", "newtest8@example.com", "Password123!")
    _create_payment_plan_budgets(client, headers)
    start = user_timezone_today()
    plan = _create_payment_plan(
        client,
        headers,
        item_name="Zero Rate Loan",
        store_or_bank_name="Family Bank",
        plan_type="BANK_LOAN",
        total_price=3_000_000,
        down_payment=0,
        months=3,
        frequency="MONTHLY",
        start_date=start.isoformat(),
        expense_category="Transport",
    )
    # Plan stores AMORTIZED_LOAN as schedule_model (it's a BANK_LOAN default)
    # but row generation used flat-total fallback since rate is 0
    assert plan["remaining_amount"] == 3_000_000
    assert len(plan["payments"]) == 3
    # All rows should be PRINCIPAL (no CHARGE rows with 0% interest)
    for p in plan["payments"]:
        assert p["component_type"] == "PRINCIPAL"
    # Even division: 1,000,000 each
    for p in plan["payments"]:
        assert p["amount"] == 1_000_000


def test_amortized_non_monthly_biweekly_frequency(client):
    """Preview amortized schedule with BIWEEKLY frequency."""
    headers = create_user_and_token(client, "newtest9", "newtest9@example.com", "Password123!")
    start = user_timezone_today()
    response = client.post(
        "/payment-plans/preview",
        json={
            "plan_type": "BANK_LOAN",
            "schedule_model": "AMORTIZED_LOAN",
            "principal": 2_000_000,
            "annual_interest_rate": 12.0,
            "payment_count": 4,
            "frequency": "BIWEEKLY",
            "first_due_date": start.isoformat(),
        },
        headers=headers,
    )
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["schedule_model"] == "AMORTIZED_LOAN"
    assert data["frequency"] == "BIWEEKLY"
    assert data["payment_count"] == 4
    # 4 installments, each with CHARGE + PRINCIPAL = 8 rows
    assert len(data["rows"]) == 8


def test_preview_rejects_past_first_due_date(client):
    """Preview with a first_due_date in the past returns 400."""
    headers = create_user_and_token(client, "newtest10", "newtest10@example.com", "Password123!")
    from datetime import date as dt_date, timedelta
    past = dt_date.today() - timedelta(days=1)
    response = client.post(
        "/payment-plans/preview",
        json={
            "plan_type": "STORE_INSTALLMENT",
            "total_price": 5_000_000,
            "payment_count": 6,
            "frequency": "MONTHLY",
            "first_due_date": past.isoformat(),
        },
        headers=headers,
    )
    assert response.status_code == 400, response.text


def test_preview_uses_months_as_payment_count_fallback(client):
    """Preview with months but no payment_count uses months."""
    headers = create_user_and_token(client, "newtest11", "newtest11@example.com", "Password123!")
    start = user_timezone_today()
    response = client.post(
        "/payment-plans/preview",
        json={
            "plan_type": "STORE_INSTALLMENT",
            "total_price": 6_000_000,
            "months": 3,
            "frequency": "MONTHLY",
            "first_due_date": start.isoformat(),
        },
        headers=headers,
    )
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["payment_count"] == 3
    assert len(data["rows"]) == 3


def test_amortized_schedule_total_principal_matches_input(client):
    """The sum of PRINCIPAL rows must equal the input principal exactly."""
    headers = create_user_and_token(client, "newtest12", "newtest12@example.com", "Password123!")
    start = user_timezone_today()
    for principal in [1_000_000, 4_070_000, 10_000_000, 5_555_555]:
        response = client.post(
            "/payment-plans/preview",
            json={
                "plan_type": "BANK_LOAN",
                "schedule_model": "AMORTIZED_LOAN",
                "principal": principal,
                "annual_interest_rate": 15.0,
                "payment_count": 6,
                "frequency": "MONTHLY",
                "first_due_date": start.isoformat(),
            },
            headers=headers,
        )
        assert response.status_code == 200, response.text
        data = response.json()
        total_principal = sum(
            r["amount"] for r in data["rows"] if r["component_type"] == "PRINCIPAL"
        )
        assert total_principal == principal, (
            f"Principal {principal}: sum of PRINCIPAL rows = {total_principal}"
        )


# ---------------------------------------------------------------------------
# Ticket 9: Manual Contract Schedule Creation
# ---------------------------------------------------------------------------


def test_manual_schedule_preview_returns_user_entered_rows(client):
    """Preview with manual rows returns the exact rows the user entered."""
    headers = create_user_and_token(client, "manualprev1", "manualprev1@example.com", "Password123!")
    start = user_timezone_today()
    manual_rows = [
        {"due_date": start.isoformat(), "component_type": "CHARGE", "amount": 75_000, "installment_number": 1},
        {"due_date": start.isoformat(), "component_type": "PRINCIPAL", "amount": 1_330_000, "installment_number": 1},
        {"due_date": (start + timedelta(days=31)).isoformat(), "component_type": "CHARGE", "amount": 45_000, "installment_number": 2},
        {"due_date": (start + timedelta(days=31)).isoformat(), "component_type": "PRINCIPAL", "amount": 1_360_000, "installment_number": 2},
    ]
    response = client.post(
        "/payment-plans/preview",
        json={
            "plan_type": "OTHER",
            "schedule_model": "MANUAL_CONTRACT_SCHEDULE",
            "manual_rows": manual_rows,
            "frequency": "MONTHLY",
            "first_due_date": start.isoformat(),
        },
        headers=headers,
    )
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["schedule_model"] == "MANUAL_CONTRACT_SCHEDULE"
    assert data["total_principal"] == 1_330_000 + 1_360_000
    assert data["total_charges"] == 75_000 + 45_000
    assert data["total_to_pay"] == data["total_principal"] + data["total_charges"]
    assert len(data["rows"]) == 4
    # Rows should preserve user-entered amounts exactly
    amounts = [r["amount"] for r in data["rows"]]
    assert 75_000 in amounts
    assert 1_330_000 in amounts
    assert 45_000 in amounts
    assert 1_360_000 in amounts


def test_manual_schedule_preview_rejects_missing_rows(client):
    """Manual preview without manual_rows returns 400."""
    headers = create_user_and_token(client, "manualprev2", "manualprev2@example.com", "Password123!")
    start = user_timezone_today()
    response = client.post(
        "/payment-plans/preview",
        json={
            "plan_type": "OTHER",
            "schedule_model": "MANUAL_CONTRACT_SCHEDULE",
            "frequency": "MONTHLY",
            "first_due_date": start.isoformat(),
        },
        headers=headers,
    )
    assert response.status_code == 400, response.text


def test_manual_schedule_preview_rejects_invalid_component_type(client):
    """Manual preview rejects rows with invalid component_type."""
    headers = create_user_and_token(client, "manualprev3", "manualprev3@example.com", "Password123!")
    start = user_timezone_today()
    response = client.post(
        "/payment-plans/preview",
        json={
            "plan_type": "OTHER",
            "schedule_model": "MANUAL_CONTRACT_SCHEDULE",
            "manual_rows": [
                {"due_date": start.isoformat(), "component_type": "INVALID", "amount": 100_000},
            ],
            "frequency": "MONTHLY",
            "first_due_date": start.isoformat(),
        },
        headers=headers,
    )
    assert response.status_code == 400, response.text


def test_manual_schedule_preview_rejects_zero_amount(client):
    """Manual preview rejects rows with zero or negative amount."""
    headers = create_user_and_token(client, "manualprev4", "manualprev4@example.com", "Password123!")
    start = user_timezone_today()
    response = client.post(
        "/payment-plans/preview",
        json={
            "plan_type": "OTHER",
            "schedule_model": "MANUAL_CONTRACT_SCHEDULE",
            "manual_rows": [
                {"due_date": start.isoformat(), "component_type": "PRINCIPAL", "amount": -100},
            ],
            "frequency": "MONTHLY",
            "first_due_date": start.isoformat(),
        },
        headers=headers,
    )
    # Zero is rejected by Pydantic (gt=0), negative is rejected by domain logic
    assert response.status_code in (400, 422), response.text


def test_manual_schedule_preview_auto_assigns_installment_numbers(client):
    """Manual rows without installment_number get them auto-assigned by due_date."""
    headers = create_user_and_token(client, "manualprev5", "manualprev5@example.com", "Password123!")
    start = user_timezone_today()
    response = client.post(
        "/payment-plans/preview",
        json={
            "plan_type": "OTHER",
            "schedule_model": "MANUAL_CONTRACT_SCHEDULE",
            "manual_rows": [
                {"due_date": start.isoformat(), "component_type": "CHARGE", "amount": 50_000},
                {"due_date": start.isoformat(), "component_type": "PRINCIPAL", "amount": 500_000},
                {"due_date": (start + timedelta(days=31)).isoformat(), "component_type": "PRINCIPAL", "amount": 500_000},
            ],
            "frequency": "MONTHLY",
            "first_due_date": start.isoformat(),
        },
        headers=headers,
    )
    assert response.status_code == 200, response.text
    data = response.json()
    # Same due_date rows should share installment number
    inst_nums = [r["installment_number"] for r in data["rows"]]
    assert inst_nums[0] == inst_nums[1]  # CHARGE + PRINCIPAL same installment
    assert inst_nums[1] != inst_nums[2]  # Different due date = different installment


def test_manual_schedule_creation_preserves_user_rows(client):
    """Creating a plan with manual rows stores exact row amounts."""
    headers = create_user_and_token(client, "manualcreate1", "manualcreate1@example.com", "Password123!")
    _create_payment_plan_budgets(client, headers)
    start = user_timezone_today()

    plan = _create_payment_plan(
        client,
        headers,
        item_name="Exact Contract",
        plan_type="OTHER",
        schedule_model="MANUAL_CONTRACT_SCHEDULE",
        total_price=2_810_000,
        down_payment=0,
        months=2,
        frequency="MONTHLY",
        start_date=start.isoformat(),
        expense_category="Electronics",
        manual_rows=[
            {"due_date": start.isoformat(), "component_type": "CHARGE", "amount": 75_000, "installment_number": 1},
            {"due_date": start.isoformat(), "component_type": "PRINCIPAL", "amount": 1_330_000, "installment_number": 1},
            {"due_date": (start + timedelta(days=31)).isoformat(), "component_type": "CHARGE", "amount": 45_000, "installment_number": 2},
            {"due_date": (start + timedelta(days=31)).isoformat(), "component_type": "PRINCIPAL", "amount": 1_360_000, "installment_number": 2},
        ],
    )
    assert plan["schedule_model"] == "MANUAL_CONTRACT_SCHEDULE"
    assert plan["schedule_rule"]["source"] == "MANUAL_CONTRACT_SCHEDULE"
    payments = plan["payments"]
    assert len(payments) == 4
    # Exact amounts preserved
    amounts = sorted([p["amount"] for p in payments])
    assert amounts == [45_000, 75_000, 1_330_000, 1_360_000]


# ---------------------------------------------------------------------------
# Ticket 10: Row Settlement State & Derived Overdue
# ---------------------------------------------------------------------------


def test_payment_row_settlement_state_unpaid(client):
    """Fresh rows have settlement_state = UNPAID."""
    headers = create_user_and_token(client, "settle1", "settle1@example.com", "Password123!")
    _create_payment_plan_budgets(client, headers)
    plan = _create_payment_plan(client, headers)
    for p in plan["payments"]:
        assert p["settlement_state"] == "UNPAID"
        assert p["settlement_label"] == "unpaid"
        assert p["remaining_amount"] == p["amount"]


def test_payment_row_settlement_state_partial_after_payment(client, session):
    """A partially paid row shows settlement_state = PARTIAL."""
    headers = create_user_and_token(client, "settle2", "settle2@example.com", "Password123!")
    _create_payment_plan_budgets(client, headers)
    plan = _create_payment_plan(client, headers)

    # Make a partial payment on the first row
    first_row = plan["payments"][0]
    resp = client.post(
        f"/payment-plans/{plan['id']}/payments",
        json={
            "amount": first_row["amount"] // 2,
            "wallet_allocations": [{"wallet_id": _default_wallet(client, headers)["id"], "amount": first_row["amount"] // 2}],
        },
        headers=headers,
    )
    assert resp.status_code == 201, resp.text

    # Re-fetch plan to get enriched rows
    refreshed = client.get(f"/payment-plans/{plan['id']}", headers=headers).json()
    first = refreshed["payments"][0]
    assert first["settlement_state"] == "PARTIAL"
    assert first["settlement_label"] == "partial"
    assert first["remaining_amount"] == first["amount"] // 2


def test_payment_row_settlement_state_settled_after_full_payment(client, session):
    """A fully paid row shows settlement_state = SETTLED, label = paid."""
    headers = create_user_and_token(client, "settle3", "settle3@example.com", "Password123!")
    _create_payment_plan_budgets(client, headers)
    plan = _create_payment_plan(client, headers, months=2, total_price=900_000, down_payment=0)

    # Pay the first row in full
    first_row = plan["payments"][0]
    wallet_id = _default_wallet(client, headers)["id"]
    resp = client.post(
        f"/payment-plans/{plan['id']}/payments",
        json={
            "amount": first_row["amount"],
            "wallet_allocations": [{"wallet_id": wallet_id, "amount": first_row["amount"]}],
        },
        headers=headers,
    )
    assert resp.status_code == 201, resp.text

    refreshed = client.get(f"/payment-plans/{plan['id']}", headers=headers).json()
    paid_row = refreshed["payments"][0]
    assert paid_row["settlement_state"] == "SETTLED"
    assert paid_row["settlement_label"] == "paid"
    assert paid_row["remaining_amount"] == 0
    # Settled rows should have null time_status
    assert paid_row["time_status"] is None


def test_payment_row_time_status_on_track(client):
    """Future-dated unpaid rows show time_status = ON_TRACK."""
    headers = create_user_and_token(client, "settle4", "settle4@example.com", "Password123!")
    _create_payment_plan_budgets(client, headers)
    # Create plan starting next month
    from datetime import date as dt_date
    start = user_timezone_today()
    future_start = start + timedelta(days=60)
    plan = _create_payment_plan(
        client,
        headers,
        start_date=future_start.isoformat(),
        months=1,
        total_price=500_000,
        down_payment=0,
    )
    for p in plan["payments"]:
        assert p["time_status"] == "ON_TRACK"
        assert p["settlement_state"] == "UNPAID"


def test_payment_row_time_status_overdue(client):
    """Past-due unpaid rows show time_status = OVERDUE."""
    headers = create_user_and_token(client, "settle5", "settle5@example.com", "Password123!")
    _create_payment_plan_budgets(client, headers)
    # Create plan with a start date far enough in the past that the first
    # payment (start + 1 period for flat-total) is before today.
    past_date = user_timezone_today() - timedelta(days=60)
    plan = _create_payment_plan(
        client,
        headers,
        start_date=past_date.isoformat(),
        months=1,
        total_price=500_000,
        down_payment=0,
        frequency="MONTHLY",
    )
    for p in plan["payments"]:
        assert p["time_status"] == "OVERDUE"
        assert p["settlement_state"] == "UNPAID"


def test_payment_row_settlement_label_written_off(client):
    """A fully written-off row shows label = written_off."""
    headers = create_user_and_token(client, "settle6", "settle6@example.com", "Password123!")
    _create_payment_plan_budgets(client, headers)
    plan = _create_payment_plan(client, headers, months=1, total_price=500_000, down_payment=0)

    # Write off the row
    row_id = plan["payments"][0]["id"]
    resp = client.post(
        f"/payment-plans/payments/{row_id}/write-off",
        headers=headers,
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["settlement_state"] == "SETTLED"
    assert resp.json()["settlement_label"] == "written_off"
    assert resp.json()["remaining_amount"] == 0
    assert resp.json()["time_status"] is None


def test_payment_row_enriched_fields_in_list(client):
    """All rows in a list response include derived settlement and time fields."""
    headers = create_user_and_token(client, "settle7", "settle7@example.com", "Password123!")
    _create_payment_plan_budgets(client, headers)
    _create_payment_plan(client, headers, months=3, total_price=1_500_000, down_payment=0)

    response = client.get("/payment-plans", headers=headers)
    assert response.status_code == 200, response.text
    data = response.json()
    assert len(data["items"]) >= 1
    for plan in data["items"]:
        for p in plan["payments"]:
            assert "settlement_state" in p
            assert "settlement_label" in p
            assert "time_status" in p
            assert "remaining_amount" in p
            # Verify internal consistency
            if p["settlement_state"] == "UNPAID":
                assert p["remaining_amount"] == p["amount"]
            elif p["settlement_state"] == "SETTLED":
                assert p["remaining_amount"] == 0
                assert p["time_status"] is None


# ---------------------------------------------------------------------------
# Ticket 11: Waterfall CHARGE-before-PRINCIPAL ordering
# ---------------------------------------------------------------------------


def test_waterfall_pays_charge_before_principal_same_due_date(client, session):
    """Within the same due date, CHARGE rows are allocated before PRINCIPAL."""
    headers = create_user_and_token(client, "wfall1", "wfall1@example.com", "Password123!")
    _create_payment_plan_budgets(client, headers)
    wallet_id = _default_wallet(client, headers)["id"]
    start = user_timezone_today()

    # Create an amortized plan with Electronics category (budgets already exist)
    plan = _create_payment_plan(
        client, headers,
        item_name="Waterfall Test",
        plan_type="BANK_LOAN",
        total_price=2_000_000,
        down_payment=0,
        months=2,
        frequency="MONTHLY",
        start_date=start.isoformat(),
        expense_category="Electronics",
        annual_interest_rate=12.0,
    )
    payments = _sorted_payments(plan)
    # First two rows: installment 1 (CHARGE then PRINCIPAL, same due_date)
    assert len(payments) >= 3  # 2 CHARGE + 2 PRINCIPAL = 4 rows
    charge_row = [p for p in payments if p["component_type"] == "CHARGE"][0]
    principal_row = [p for p in payments if p["component_type"] == "PRINCIPAL"][0]
    assert charge_row["due_date"] == principal_row["due_date"]

    # Pay an amount that partially covers CHARGE + some PRINCIPAL
    charge_amount = charge_row["amount"]
    extra = 50_000
    pay_amount = charge_amount + extra

    resp = client.post(
        f"/payment-plans/{plan['id']}/payments",
        json={
            "amount": pay_amount,
            "wallet_allocations": [{"wallet_id": wallet_id, "amount": pay_amount}],
        },
        headers=headers,
    )
    assert resp.status_code == 201, resp.text
    details = resp.json()

    # CHARGE row should be fully paid, PRINCIPAL row partially paid
    refreshed_charge = [
        p for p in details["plan"]["payments"]
        if p["id"] == charge_row["id"]
    ][0]
    refreshed_principal = [
        p for p in details["plan"]["payments"]
        if p["id"] == principal_row["id"]
    ][0]
    assert refreshed_charge["settlement_state"] == "SETTLED"
    assert refreshed_principal["settlement_state"] == "PARTIAL"
    assert refreshed_principal["remaining_amount"] == principal_row["amount"] - extra


def test_waterfall_oversized_payment_up_to_remaining(client, session):
    """A payment equal to the total unpaid schedule is accepted (not rejected)."""
    headers = create_user_and_token(client, "wfall2", "wfall2@example.com", "Password123!")
    _create_payment_plan_budgets(client, headers)
    wallet_id = _default_wallet(client, headers)["id"]
    plan = _create_payment_plan(client, headers, months=3, total_price=900_000, down_payment=0)

    total_unpaid = sum(p["remaining_amount"] for p in plan["payments"])
    # Pay the total remaining
    resp = client.post(
        f"/payment-plans/{plan['id']}/payments",
        json={
            "amount": total_unpaid,
            "wallet_allocations": [{"wallet_id": wallet_id, "amount": total_unpaid}],
        },
        headers=headers,
    )
    assert resp.status_code == 201, resp.text
    # All rows should be settled
    for p in resp.json()["plan"]["payments"]:
        assert p["settlement_state"] == "SETTLED"


# ---------------------------------------------------------------------------
# Ticket 12: First-Class Write-Offs
# ---------------------------------------------------------------------------


def test_row_write_off_uses_wrte_off_ledger_entry_type(client, session):
    """Row write-off creates a WRITE_OFF ledger entry, not ADJUSTMENT."""
    headers = create_user_and_token(client, "woff1", "woff1@example.com", "Password123!")
    _create_payment_plan_budgets(client, headers)
    plan = _create_payment_plan(client, headers, months=1, total_price=300_000, down_payment=0)
    row = plan["payments"][0]

    resp = client.post(
        f"/payment-plans/payments/{row['id']}/write-off",
        headers=headers,
    )
    assert resp.status_code == 200, resp.text

    entry = (
        session.query(models.PaymentPlanLedgerEntry)
        .filter(
            models.PaymentPlanLedgerEntry.plan_id == plan["id"],
            models.PaymentPlanLedgerEntry.entry_type == models.PaymentPlanLedgerEntryType.WRITE_OFF,
        )
        .first()
    )
    assert entry is not None
    assert entry.event_subtype == "PAYMENT_PLAN_WRITE_OFF"
    # No ADJUSTMENT entries for this write-off
    adj_entry = (
        session.query(models.PaymentPlanLedgerEntry)
        .filter(
            models.PaymentPlanLedgerEntry.plan_id == plan["id"],
            models.PaymentPlanLedgerEntry.entry_type == models.PaymentPlanLedgerEntryType.ADJUSTMENT,
            models.PaymentPlanLedgerEntry.event_subtype == "PAYMENT_PLAN_WRITE_OFF",
        )
        .first()
    )
    assert adj_entry is None


def test_row_write_off_custom_amount(client, session):
    """Writing off a custom partial amount leaves the row PARTIAL."""
    headers = create_user_and_token(client, "woff2", "woff2@example.com", "Password123!")
    _create_payment_plan_budgets(client, headers)
    plan = _create_payment_plan(client, headers, months=1, total_price=300_000, down_payment=0)
    row = plan["payments"][0]

    # Write off only 100k of the 300k row
    resp = client.post(
        f"/payment-plans/payments/{row['id']}/write-off",
        json={"amount": 100_000, "note": "Partial forgiveness"},
        headers=headers,
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["written_off_amount"] == 100_000
    assert data["settlement_state"] == "PARTIAL"
    assert data["remaining_amount"] == 200_000


def test_plan_level_write_off_allocates_across_rows(client, session):
    """Plan-level write-off distributes across unsettled rows in waterfall order."""
    headers = create_user_and_token(client, "woff3", "woff3@example.com", "Password123!")
    _create_payment_plan_budgets(client, headers)
    plan = _create_payment_plan(client, headers, months=3, total_price=900_000, down_payment=0)
    # Each row is 300,000

    # Write off 500,000 across the plan
    resp = client.post(
        f"/payment-plans/{plan['id']}/write-off",
        json={"amount": 500_000, "note": "Seller settlement discount"},
        headers=headers,
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()

    # First row should be fully written off (300k), second partially (200k)
    rows = _sorted_payments(data["plan"])
    assert rows[0]["settlement_state"] == "SETTLED"
    assert rows[0]["written_off_amount"] == 300_000
    assert rows[0]["remaining_amount"] == 0

    assert rows[1]["settlement_state"] == "PARTIAL"
    assert rows[1]["written_off_amount"] == 200_000
    assert rows[1]["remaining_amount"] == 100_000

    # Third row untouched
    assert rows[2]["settlement_state"] == "UNPAID"
    assert rows[2]["written_off_amount"] == 0

    # Plan remaining should be 400,000 (3×300k - 500k write-off)
    assert data["plan"]["remaining_amount"] == 400_000

    # Activity should show write-off entries
    assert any(
        item["entry_type"] == "WRITE_OFF"
        for item in data["plan_activity"]
    )


def test_plan_level_write_off_rejects_excess(client, session):
    """Plan-level write-off exceeding total remaining returns 400."""
    headers = create_user_and_token(client, "woff4", "woff4@example.com", "Password123!")
    _create_payment_plan_budgets(client, headers)
    plan = _create_payment_plan(client, headers, months=1, total_price=300_000, down_payment=0)

    resp = client.post(
        f"/payment-plans/{plan['id']}/write-off",
        json={"amount": 500_000, "note": "Too much"},
        headers=headers,
    )
    assert resp.status_code == 400, resp.text


def test_write_off_does_not_create_wallet_movement(client, session):
    """Write-offs (row and plan) do not create wallet ledger entries."""
    headers = create_user_and_token(client, "woff5", "woff5@example.com", "Password123!")
    _create_payment_plan_budgets(client, headers)
    plan = _create_payment_plan(client, headers, months=2, total_price=600_000, down_payment=0)

    # Row write-off
    row_id = plan["payments"][0]["id"]
    client.post(f"/payment-plans/payments/{row_id}/write-off", headers=headers)

    # Plan write-off
    client.post(
        f"/payment-plans/{plan['id']}/write-off",
        json={"amount": 300_000, "note": "Plan-level"},
        headers=headers,
    )

    # Verify no wallet movement for write-off entries
    write_off_entries = (
        session.query(models.PaymentPlanLedgerEntry)
        .filter(
            models.PaymentPlanLedgerEntry.plan_id == plan["id"],
            models.PaymentPlanLedgerEntry.entry_type == models.PaymentPlanLedgerEntryType.WRITE_OFF,
        )
        .all()
    )
    assert len(write_off_entries) == 2
    for entry in write_off_entries:
        assert entry.financial_event_id is None  # No wallet event linked


# ---------------------------------------------------------------------------
# Ticket 13: Append-Only Reversals
# ---------------------------------------------------------------------------


def test_write_off_undo_is_append_only(client, session):
    """Undoing a write-off preserves the original WRITE_OFF entry and appends REVERSAL."""
    headers = create_user_and_token(client, "rev1", "rev1@example.com", "Password123!")
    _create_payment_plan_budgets(client, headers)
    plan = _create_payment_plan(client, headers, months=1, total_price=300_000, down_payment=0)
    row = plan["payments"][0]

    # Write off the row
    client.post(f"/payment-plans/payments/{row['id']}/write-off", headers=headers)

    # Undo the write-off
    undone = client.post(f"/payment-plans/payments/{row['id']}/undo-write-off", headers=headers)
    assert undone.status_code == 200, undone.text

    # Original WRITE_OFF should still exist
    write_off_entry = (
        session.query(models.PaymentPlanLedgerEntry)
        .filter(
            models.PaymentPlanLedgerEntry.plan_id == plan["id"],
            models.PaymentPlanLedgerEntry.entry_type == models.PaymentPlanLedgerEntryType.WRITE_OFF,
        )
        .first()
    )
    assert write_off_entry is not None, "Original WRITE_OFF entry must be preserved"

    # REVERSAL entry should exist
    reversal_entry = (
        session.query(models.PaymentPlanLedgerEntry)
        .filter(
            models.PaymentPlanLedgerEntry.plan_id == plan["id"],
            models.PaymentPlanLedgerEntry.entry_type == models.PaymentPlanLedgerEntryType.REVERSAL,
        )
        .first()
    )
    assert reversal_entry is not None, "REVERSAL entry must be created"

    # Row state restored
    data = undone.json()
    assert data["written_off_amount"] == 0
    assert data["settlement_state"] == "UNPAID"


def test_undo_charge_creates_reversal_entry(client, session):
    """Undoing a charge appends a REVERSAL entry and preserves the original CHARGE."""
    headers = create_user_and_token(client, "rev2", "rev2@example.com", "Password123!")
    _create_payment_plan_budgets(client, headers)
    plan = _create_payment_plan(client, headers, months=1, total_price=300_000, down_payment=0)

    # Add a charge
    client.post(
        f"/payment-plans/{plan['id']}/charges",
        json={"charge_type": "FEE", "amount": 50_000},
        headers=headers,
    )

    # Undo the charge
    undone = client.post(f"/payment-plans/{plan['id']}/charges/undo-latest", headers=headers)
    assert undone.status_code == 200, undone.text

    # Original CHARGE should still exist
    charge_entry = (
        session.query(models.PaymentPlanLedgerEntry)
        .filter(
            models.PaymentPlanLedgerEntry.plan_id == plan["id"],
            models.PaymentPlanLedgerEntry.entry_type == models.PaymentPlanLedgerEntryType.CHARGE,
        )
        .first()
    )
    assert charge_entry is not None, "Original CHARGE entry must be preserved"

    # REVERSAL should exist
    reversal_entry = (
        session.query(models.PaymentPlanLedgerEntry)
        .filter(
            models.PaymentPlanLedgerEntry.plan_id == plan["id"],
            models.PaymentPlanLedgerEntry.entry_type == models.PaymentPlanLedgerEntryType.REVERSAL,
        )
        .first()
    )
    assert reversal_entry is not None, "REVERSAL entry must be created"


# ---------------------------------------------------------------------------
# Ticket 14: Derived Plan Totals & Archive
# ---------------------------------------------------------------------------


def test_plan_response_includes_derived_totals(client):
    """Plan response includes remaining_principal, remaining_charges, lifecycle, time_status."""
    headers = create_user_and_token(client, "derived1", "derived1@example.com", "Password123!")
    _create_payment_plan_budgets(client, headers)
    plan = _create_payment_plan(client, headers, months=3, total_price=900_000, down_payment=0)

    assert "remaining_principal" in plan
    assert "remaining_charges" in plan
    assert "lifecycle_status" in plan
    assert "time_status" in plan
    assert plan["lifecycle_status"] == "OPEN"
    assert plan["time_status"] == "ON_TRACK"
    # Flat-total plan: all remaining is principal, zero charges
    assert plan["remaining_principal"] == 900_000
    assert plan["remaining_charges"] == 0


def test_plan_lifecycle_closed_when_fully_paid(client, session):
    """A fully paid plan shows lifecycle_status = CLOSED and time_status = null."""
    headers = create_user_and_token(client, "derived2", "derived2@example.com", "Password123!")
    _create_payment_plan_budgets(client, headers)
    wallet_id = _default_wallet(client, headers)["id"]
    plan = _create_payment_plan(client, headers, months=1, total_price=300_000, down_payment=0)

    # Pay in full
    client.post(
        f"/payment-plans/{plan['id']}/payments",
        json={"amount": 300_000, "wallet_allocations": [{"wallet_id": wallet_id, "amount": 300_000}]},
        headers=headers,
    )

    refreshed = client.get(f"/payment-plans/{plan['id']}", headers=headers).json()
    assert refreshed["lifecycle_status"] == "CLOSED"
    assert refreshed["time_status"] is None
    assert refreshed["remaining_amount"] == 0
    assert refreshed["remaining_principal"] == 0
    assert refreshed["remaining_charges"] == 0


def test_archive_preserves_financial_state(client, session):
    """Archiving a plan sets archived_at but does not change lifecycle or time status."""
    headers = create_user_and_token(client, "archive1", "archive1@example.com", "Password123!")
    _create_payment_plan_budgets(client, headers)
    plan = _create_payment_plan(client, headers, months=1, total_price=300_000, down_payment=0)

    # Archive
    archived = client.post(f"/payment-plans/{plan['id']}/archive", headers=headers)
    assert archived.status_code == 200, archived.text
    data = archived.json()
    assert data["archived_at"] is not None
    assert data["lifecycle_status"] == "OPEN"  # Still open — balance hasn't changed
    assert data["remaining_amount"] == 300_000  # Balances unchanged
    assert len(data["payments"]) == 1  # Rows unchanged


def test_unarchive_clears_archived_at(client, session):
    """Unarchiving clears archived_at without touching financial data."""
    headers = create_user_and_token(client, "archive2", "archive2@example.com", "Password123!")
    _create_payment_plan_budgets(client, headers)
    plan = _create_payment_plan(client, headers, months=1, total_price=300_000, down_payment=0)

    client.post(f"/payment-plans/{plan['id']}/archive", headers=headers)
    restored = client.post(f"/payment-plans/{plan['id']}/unarchive", headers=headers)
    assert restored.status_code == 200, restored.text
    data = restored.json()
    assert data["archived_at"] is None
    assert data["lifecycle_status"] == "OPEN"
    assert data["remaining_amount"] == 300_000


def test_pristine_delete_allowed_after_archive_restore(client):
    """A plan that was archived and restored but never had payments is still pristine."""
    headers = create_user_and_token(client, "archive3", "archive3@example.com", "Password123!")
    _create_payment_plan_budgets(client, headers)
    plan = _create_payment_plan(client, headers, months=1, total_price=300_000, down_payment=0)

    # Archive and restore — no financial activity
    client.post(f"/payment-plans/{plan['id']}/archive", headers=headers)
    client.post(f"/payment-plans/{plan['id']}/unarchive", headers=headers)

    # Should still be deletable (pristine check uses activity, not archive state)
    resp = client.delete(f"/payment-plans/{plan['id']}", headers=headers)
    assert resp.status_code == 204


# ---------------------------------------------------------------------------
# Ticket 15: Cross-Domain Regression
# ---------------------------------------------------------------------------


def test_payment_plan_payment_does_not_create_debt_ledger_entries(client, session):
    """A payment plan payment must not create rows in the Debt ledger."""
    headers = create_user_and_token(client, "xdomain1", "xdomain1@example.com", "Password123!")
    _create_payment_plan_budgets(client, headers)
    wallet_id = _default_wallet(client, headers)["id"]
    plan = _create_payment_plan(client, headers, months=1, total_price=300_000, down_payment=0)

    # Count Debt ledger entries before
    before = session.query(models.DebtLedgerEntry).count()

    client.post(
        f"/payment-plans/{plan['id']}/payments",
        json={"amount": 300_000, "wallet_allocations": [{"wallet_id": wallet_id, "amount": 300_000}]},
        headers=headers,
    )

    after = session.query(models.DebtLedgerEntry).count()
    assert after == before, "Payment Plan payment must not create Debt ledger entries"


def test_payment_plan_ledger_uses_only_plan_owned_types(client, session):
    """All Payment Plan ledger entries use Payment Plan entry types, not Debt types."""
    headers = create_user_and_token(client, "xdomain2", "xdomain2@example.com", "Password123!")
    _create_payment_plan_budgets(client, headers)
    wallet_id = _default_wallet(client, headers)["id"]
    plan = _create_payment_plan(client, headers, months=1, total_price=300_000, down_payment=0)

    # Create payment
    client.post(
        f"/payment-plans/{plan['id']}/payments",
        json={"amount": 150_000, "wallet_allocations": [{"wallet_id": wallet_id, "amount": 150_000}]},
        headers=headers,
    )
    # Write off
    row_id = plan["payments"][0]["id"]
    client.post(f"/payment-plans/payments/{row_id}/write-off", json={"amount": 50_000}, headers=headers)

    # All entries should use Payment Plan types
    entries = (
        session.query(models.PaymentPlanLedgerEntry)
        .filter(models.PaymentPlanLedgerEntry.plan_id == plan["id"])
        .all()
    )
    valid_types = {e.value for e in models.PaymentPlanLedgerEntryType}
    for entry in entries:
        assert entry.entry_type.value in valid_types, (
            f"Entry {entry.id} has unexpected type: {entry.entry_type}"
        )


def test_plan_response_does_not_leak_debt_vocabulary(client):
    """Payment Plan responses must not contain Debt product-kind or legacy status values."""
    headers = create_user_and_token(client, "xdomain3", "xdomain3@example.com", "Password123!")
    _create_payment_plan_budgets(client, headers)
    plan = _create_payment_plan(client, headers, months=1, total_price=300_000, down_payment=0)

    plan_str = str(plan)
    # No Debt product vocabulary
    for banned in ("MORTGAGE", "CLIENT_RECEIVABLE", "PERSONAL_REIMBURSEMENT", "INFORMAL_DEBT"):
        assert banned not in plan_str, f"Debt product vocabulary leaked: {banned}"

    # Row status should use settlement state, not legacy SKIPPED as primary
    for p in plan["payments"]:
        assert "settlement_state" in p


def test_timezone_consistency_across_plan_responses(client):
    """Plan time_status uses effective user timezone for overdue derivation."""
    headers = create_user_and_token(client, "xdomain4", "xdomain4@example.com", "Password123!")
    # Set an explicit timezone
    headers["X-Timezone"] = "Asia/Tashkent"
    _create_payment_plan_budgets(client, headers)

    # Create plan with past due date — should be overdue in any reasonable tz
    from datetime import date as dt_date, timedelta
    past = dt_date.today() - timedelta(days=60)
    plan = _create_payment_plan(
        client, headers,
        start_date=past.isoformat(),
        months=1,
        total_price=300_000,
        down_payment=0,
        frequency="MONTHLY",
    )
    # First payment = past + 1 month ≈ 30 days ago → should be overdue
    assert plan["time_status"] == "OVERDUE"


def test_immutable_history_no_hard_delete_in_write_off_flow(client, session):
    """Write-off flow must never hard-delete posted ledger entries."""
    headers = create_user_and_token(client, "xdomain5", "xdomain5@example.com", "Password123!")
    _create_payment_plan_budgets(client, headers)
    plan = _create_payment_plan(client, headers, months=1, total_price=300_000, down_payment=0)
    row = plan["payments"][0]

    # Capture count before write-off
    before_entries = (
        session.query(models.PaymentPlanLedgerEntry)
        .filter(models.PaymentPlanLedgerEntry.plan_id == plan["id"])
        .count()
    )

    # Write off
    client.post(f"/payment-plans/payments/{row['id']}/write-off", headers=headers)

    # Undo write-off
    client.post(f"/payment-plans/payments/{row['id']}/undo-write-off", headers=headers)

    # After undo, we should have MORE entries than before (original + WRITE_OFF + REVERSAL)
    after_entries = (
        session.query(models.PaymentPlanLedgerEntry)
        .filter(models.PaymentPlanLedgerEntry.plan_id == plan["id"])
        .count()
    )
    assert after_entries > before_entries, (
        f"Expected entries to grow (append-only), but got {before_entries} → {after_entries}"
    )
