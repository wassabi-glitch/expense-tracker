from app import models
from tests.helpers import create_user_and_token, user_timezone_today

def _user(session, email: str) -> models.User:
    return session.query(models.User).filter(models.User.email == email).one()

def test_future_timeline_aggregates_all_event_types(client, session):
    email = "timeline_test@example.com"
    headers = create_user_and_token(client, "timeliner", email, "Password123!")
    user = _user(session, email)
    today = user_timezone_today()

    # 1. Expected Income
    source = models.IncomeSource(
        owner_id=user.id,
        name="Job",
        is_active=True
    )
    session.add(source)
    session.flush()

    income_promise = models.ExpectedInflowPromise(
        owner_id=user.id,
        kind=models.ExpectedInflowKind.EARNED,
        source_id=source.id,
        title="Monthly Salary",
        original_amount=1_000_000,
        status=models.ExpectedInflowPromiseStatus.EXPECTED,
    )
    session.add(income_promise)
    session.flush()

    income = models.ExpectedIncome(
        owner_id=user.id,
        promise_id=income_promise.id,
        kind=models.ExpectedInflowKind.EARNED,
        source_id=source.id,
        amount=1_000_000,
        due_date=today,
        budget_year=today.year,
        budget_month=today.month,
        status=models.ExpectedIncomeStatus.EXPECTED
    )

    # 2. Debt Owing
    debt = models.Debt(
        owner_id=user.id,
        debt_type=models.DebtType.OWING,
        origin_kind=models.DebtOriginKind.CASH_BORROWED,
        counterparty_kind=models.DebtCounterpartyKind.PERSON,
        counterparty_name="John Doe",
        initial_amount=500_000,
        remaining_amount=500_000,
        status=models.DebtStatus.ACTIVE,
        date=today,
        expected_return_date=today,
    )

    # 3. Debt Owed: open receivables should not appear unless the user creates
    # an explicit expected inflow.
    debt_owed = models.Debt(
        owner_id=user.id,
        debt_type=models.DebtType.OWED,
        origin_kind=models.DebtOriginKind.CASH_LENT,
        counterparty_kind=models.DebtCounterpartyKind.PERSON,
        counterparty_name="Jane Doe",
        initial_amount=200_000,
        remaining_amount=200_000,
        status=models.DebtStatus.ACTIVE,
        date=today,
        expected_return_date=today,
    )

    # 4. Payment Plan Payment
    plan = models.PaymentPlan(
        owner_id=user.id,
        item_name="Phone",
        plan_type=models.PaymentPlanType.STORE_INSTALLMENT,
        total_price=500_000,
        down_payment=0,
        remaining_amount=500_000,
        months=1,
        payment_count=1,
        frequency=models.PaymentPlanFrequency.MONTHLY,
        monthly_payment_amount=500_000,
        regular_payment_amount=500_000,
        status=models.PaymentPlanStatus.ACTIVE,
        start_date=today,
        expense_category=models.ExpenseCategory.ELECTRONICS,
    )

    # 5. Recurring Expense
    recurring = models.RecurringExpense(
        owner_id=user.id,
        title="Netflix",
        amount=50_000,
        category=models.ExpenseCategory.ENTERTAINMENT,
        frequency=models.RecurringFrequency.MONTHLY,
        start_date=today,
        next_due_date=today,
        status=models.RecurringStatus.ACTIVE
    )

    session.add_all([income, debt, debt_owed, plan, recurring])
    session.flush()

    payment_plan_payment = models.PaymentPlanPayment(
        owner_id=user.id,
        plan_id=plan.id,
        amount=500_000,
        paid_amount=0,
        written_off_amount=0,
        status=models.PaymentPlanPaymentStatus.PENDING,
        due_date=today,
    )
    
    recurring_occ = models.RecurringOccurrence(
        owner_id=user.id,
        template_id=recurring.id,
        expected_amount=50_000,
        expected_title="Netflix",
        expected_category=models.ExpenseCategory.ENTERTAINMENT,
        status=models.RecurringOccurrenceStatus.PENDING_CONFIRMATION,
        scheduled_due_date=today
    )
    
    session.add_all([payment_plan_payment, recurring_occ])
    session.commit()

    res = client.get(
        f"/budgets/timeline?budget_year={today.year}&budget_month={today.month}",
        headers=headers,
    )
    
    assert res.status_code == 200, res.text
    data = res.json()
    assert "items" in data
    
    events = data["items"]
    assert len(events) == 4
    
    titles = [e["title"] for e in events]
    assert "Monthly Salary" in titles
    assert "Pay Debt: John Doe" in titles
    assert "Receive Debt: Jane Doe" not in titles
    assert "Payment plan: Phone" in titles
    assert "Netflix" in titles

    # Verify directions
    income_ev = next(e for e in events if e["title"] == "Monthly Salary")
    assert income_ev["direction"] == "INFLOW"
    assert income_ev["event_type"] == "EXPECTED_INFLOW"

    debt_owing_ev = next(e for e in events if e["title"] == "Pay Debt: John Doe")
    assert debt_owing_ev["direction"] == "OUTFLOW"
    assert debt_owing_ev["event_type"] == "DEBT_PAYMENT"
    assert debt_owing_ev["source_type"] == "DEBT"
    assert debt_owing_ev["debt_id"] == debt.id
    assert debt_owing_ev["payment_plan_id"] is None

    install_ev = next(e for e in events if e["title"] == "Payment plan: Phone")
    assert install_ev["direction"] == "OUTFLOW"
    assert install_ev["event_type"] == "PAYMENT_PLAN"
    assert install_ev["source_type"] == "PAYMENT_PLAN_PAYMENT"
    assert install_ev["payment_plan_id"] == plan.id
    assert install_ev["payment_plan_payment_id"] == payment_plan_payment.id
    assert install_ev["debt_id"] is None

    rec_ev = next(e for e in events if e["title"] == "Netflix")
    assert rec_ev["direction"] == "OUTFLOW"
    assert rec_ev["event_type"] == "RECURRING_EXPENSE"
    assert rec_ev["source_type"] == "RECURRING_OCCURRENCE"


def test_timeline_uses_payment_plan_schedule_rows_not_linked_debt(client, session):
    email = "timeline_plan_schedule@example.com"
    headers = create_user_and_token(client, "timelineplanschedule", email, "Password123!")
    user = _user(session, email)
    today = user_timezone_today()

    linked_debt = models.Debt(
        owner_id=user.id,
        debt_type=models.DebtType.OWING,
        origin_kind=models.DebtOriginKind.FINANCED_ASSET_PURCHASE,
        counterparty_kind=models.DebtCounterpartyKind.STORE,
        counterparty_name="Hidden phone debt",
        initial_amount=500_000,
        remaining_amount=500_000,
        status=models.DebtStatus.ACTIVE,
        date=today,
        expected_return_date=today,
        expense_category=models.ExpenseCategory.ELECTRONICS,
    )
    session.add(linked_debt)
    session.flush()
    plan = models.PaymentPlan(
        owner_id=user.id,
        debt_id=linked_debt.id,
        item_name="Phone",
        plan_type=models.PaymentPlanType.STORE_INSTALLMENT,
        total_price=500_000,
        down_payment=0,
        remaining_amount=500_000,
        months=2,
        payment_count=2,
        frequency=models.PaymentPlanFrequency.MONTHLY,
        monthly_payment_amount=250_000,
        regular_payment_amount=250_000,
        status=models.PaymentPlanStatus.ACTIVE,
        start_date=today,
        expense_category=models.ExpenseCategory.ELECTRONICS,
    )
    session.add(plan)
    session.flush()
    payment = models.PaymentPlanPayment(
        owner_id=user.id,
        plan_id=plan.id,
        amount=250_000,
        paid_amount=100_000,
        written_off_amount=0,
        component_type=models.PaymentPlanPaymentComponentType.PRINCIPAL,
        status=models.PaymentPlanPaymentStatus.PARTIAL,
        due_date=today,
    )
    session.add(payment)
    session.commit()

    res = client.get(
        f"/budgets/timeline?budget_year={today.year}&budget_month={today.month}",
        headers=headers,
    )

    assert res.status_code == 200, res.text
    events = res.json()["items"]
    assert len(events) == 1
    assert events[0]["event_type"] == "PAYMENT_PLAN"
    assert events[0]["source_type"] == "PAYMENT_PLAN_PAYMENT"
    assert events[0]["source_id"] == payment.id
    assert events[0]["payment_plan_id"] == plan.id
    assert events[0]["payment_plan_payment_id"] == payment.id
    assert events[0]["debt_id"] is None
    assert events[0]["amount"] == 150_000


def test_timeline_excludes_fully_paid_items_and_uses_remaining_amount(client, session):
    email = "timeline_partial@example.com"
    headers = create_user_and_token(client, "partial", email, "Password123!")
    user = _user(session, email)
    today = user_timezone_today()

    # Debt partially paid
    debt = models.Debt(
        owner_id=user.id,
        debt_type=models.DebtType.OWING,
        origin_kind=models.DebtOriginKind.CASH_BORROWED,
        counterparty_kind=models.DebtCounterpartyKind.PERSON,
        counterparty_name="Bob",
        initial_amount=1_000_000,
        remaining_amount=200_000,
        status=models.DebtStatus.ACTIVE,
        date=today,
        expected_return_date=today,
    )
    
    # Expected income fully received
    source = models.IncomeSource(
        owner_id=user.id,
        name="BonusSource",
        is_active=True
    )
    session.add(source)
    session.flush()

    income_promise = models.ExpectedInflowPromise(
        owner_id=user.id,
        kind=models.ExpectedInflowKind.EARNED,
        source_id=source.id,
        title="Bonus",
        original_amount=1_000_000,
        status=models.ExpectedInflowPromiseStatus.RESOLVED,
    )
    session.add(income_promise)
    session.flush()

    income = models.ExpectedIncome(
        owner_id=user.id,
        promise_id=income_promise.id,
        kind=models.ExpectedInflowKind.EARNED,
        source_id=source.id,
        amount=1_000_000,
        due_date=today,
        budget_year=today.year,
        budget_month=today.month,
        status=models.ExpectedIncomeStatus.RESOLVED
    )

    session.add_all([debt, income])
    session.commit()

    res = client.get(
        f"/budgets/timeline?budget_year={today.year}&budget_month={today.month}",
        headers=headers,
    )
    
    assert res.status_code == 200, res.text
    events = res.json()["items"]
    
    assert len(events) == 1
    assert events[0]["title"] == "Pay Debt: Bob"
    assert events[0]["amount"] == 200_000
