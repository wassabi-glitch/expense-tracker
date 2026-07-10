from datetime import timedelta
from app import models
from tests.helpers import create_user_and_token, create_budget, create_expense, user_timezone_today


def test_analytics_history(client, session):
    headers = create_user_and_token(
        client, "analyticsuser", "analyticsuser@example.com", "Password123!"
    )

    # Add two expenses.
    create_budget(client, headers, category="Food", monthly_limit=50000)
    create_expense(client, headers, title="Item One", amount=10, category="Food")
    create_expense(client, headers, title="Item Two", amount=20, category="Food")

    res = client.get("/analytics/history", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert data["total_spent_lifetime"] == 30
    assert data["total_transaction"] == 2


def test_analytics_daily_trend(client):
    headers = create_user_and_token(
        client, "trenduser", "trenduser@example.com", "Password123!"
    )
    create_budget(client, headers, category="Food", monthly_limit=500)

    today = user_timezone_today()
    # Only use yesterday if it's the same month, otherwise use today
    if today.day > 1:
        expense_date = today - timedelta(days=1)
    else:
        expense_date = today
    create_expense(client, headers, title="Yes", amount=5, category="Food",
                   expense_date=expense_date)

    res = client.get("/analytics/daily-trend?days=2", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert len(data) >= 1  # At least the expense day is returned


def test_daily_trend_days_filter(client):
    headers = create_user_and_token(
        client, "daysfilteruser", "daysfilteruser@example.com", "Password123!"
    )
    create_budget(client, headers, category="Food", monthly_limit=500)

    # Create expense for today (always in same month as budget)
    create_expense(client, headers, title="Today Expense",
                   amount=10, category="Food")

    # days=2 should return at most 2 entries; our expense should be included
    res = client.get("/analytics/daily-trend?days=2", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert 1 <= len(data) <= 2
    # Verify our expense appears in the results
    amounts = [d["amount"] for d in data]
    assert 10 in amounts


def test_analytic_daily_trend_invalid_days(client):
    headers = create_user_and_token(
        client, "invaliddayuser", "invaliddayuser@example.com", "Password123!"
    )
    create_budget(client, headers, category="Food", monthly_limit=500)

    # Don't create expenses with dates that have no budget
    # Just test the validation endpoints directly
    res1 = client.get("/analytics/daily-trend?days=0", headers=headers)
    res2 = client.get("/analytics/daily-trend?days=400", headers=headers)
    assert res1.status_code == 400
    assert res2.status_code == 400

    today = user_timezone_today()
    just_within = today - timedelta(days=365)

    res_missing_end = client.get(
        f"/analytics/daily-trend?start_date={just_within.isoformat()}",
        headers=headers,
    )
    res_missing_start = client.get(
        f"/analytics/daily-trend?end_date={today.isoformat()}",
        headers=headers,
    )
    assert res_missing_end.status_code == 400
    assert res_missing_start.status_code == 400

    res3 = client.get(
        f"/analytics/daily-trend?start_date={just_within.isoformat()}&end_date={today.isoformat()}",
        headers=headers,
    )
    assert res3.status_code == 200
    assert len(res3.json()) >= 1  # At least 1 day in the range


def test_daily_trend_date_range_filters(client):
    headers = create_user_and_token(
        client, "daterangeuser", "daterangeuser@example.com", "Password123!"
    )
    create_budget(client, headers, category="Food", monthly_limit=500)

    today = user_timezone_today()
    # Use dates that stay within the same month
    if today.day >= 3:
        two_days_ago = today.replace(day=today.day - 2)
        one_day_ago = today.replace(day=today.day - 1)
    else:
        # Near start of month — just use today and yesterday (if safe)
        two_days_ago = today
        one_day_ago = today

    create_expense(client, headers, title="Two Days", amount=10, category="Food",
                   expense_date=two_days_ago)
    if one_day_ago != two_days_ago:
        create_expense(client, headers, title="One Day", amount=10, category="Food",
                       expense_date=one_day_ago)

    res = client.get(
        f"/analytics/daily-trend?start_date={two_days_ago.isoformat()}&end_date={one_day_ago.isoformat()}",
        headers=headers,
    )
    assert res.status_code == 200
    data = res.json()
    expected_days = (one_day_ago - two_days_ago).days + 1
    assert len(data) == expected_days


def test_daily_trend_invalid_range(client):
    headers = create_user_and_token(
        client, "invalidrangeuser", "invalidrangeuser@example.com", "Password123!"
    )
    create_budget(client, headers, category="Food", monthly_limit=500)

    today = user_timezone_today()
    yesterday = today - timedelta(days=1)

    res = client.get(
        f"/analytics/daily-trend?start_date={today.isoformat()}&end_date={yesterday.isoformat()}",
        headers=headers,
    )
    assert res.status_code == 400


def test_daily_trend_rejects_dates_before_2020(client):
    headers = create_user_and_token(
        client, "mindateuser", "mindateuser@example.com", "Password123!"
    )
    create_budget(client, headers, category="Food", monthly_limit=500)

    res = client.get(
        "/analytics/daily-trend?start_date=2019-12-31&end_date=2020-01-02",
        headers=headers,
    )
    assert res.status_code == 400
    assert "date_too_early" in res.text


def test_category_breakdown_rejects_dates_before_2020(client):
    headers = create_user_and_token(
        client, "mincatuser", "mincatuser@example.com", "Password123!"
    )
    create_budget(client, headers, category="Food", monthly_limit=500)

    res = client.get(
        "/analytics/category-breakdown?start_date=2019-12-31&end_date=2020-01-02",
        headers=headers,
    )
    assert res.status_code == 400
    assert "date_too_early" in res.text


def test_dashboard_summary_positive_remaining(client):
    headers = create_user_and_token(
        client, "summarypos", "summarypos@example.com", "Password123!"
    )

    onboard = client.post(
        "/users/me/onboarding",
        json={
            "life_statuses": ["employed"],
            "wallets": [{"name": "Cash", "initial_balance": 1_000_000}],
        },
        headers=headers,
    )
    assert onboard.status_code == 200

    create_budget(client, headers, category="Food", monthly_limit=500_000)
    created = create_expense(client, headers, title="Food", amount=250_000, category="Food")
    assert created.status_code == 201

    res = client.get("/analytics/dashboard-summary", headers=headers)
    assert res.status_code == 200
    data = res.json()

    assert data["income"] == 0
    assert data["spent"] == 250_000
    assert data["remaining"] == -250_000
    assert data["overall_balance"] == 750_000
    assert data["daily_average"] == round(250_000 / max(1, user_timezone_today().day))


def test_dashboard_summary_negative_remaining(client):
    headers = create_user_and_token(
        client, "summaryneg", "summaryneg@example.com", "Password123!"
    )

    onboard = client.post(
        "/users/me/onboarding",
        json={
            "life_statuses": ["self_employed"],
            "wallets": [{"name": "Cash", "initial_balance": 500_000}],
        },
        headers=headers,
    )
    assert onboard.status_code == 200

    create_budget(client, headers, category="Food", monthly_limit=400_000)
    created = create_expense(client, headers, title="Food", amount=360_000, category="Food")
    assert created.status_code == 201

    res = client.get("/analytics/dashboard-summary", headers=headers)
    assert res.status_code == 200
    data = res.json()

    assert data["income"] == 0
    assert data["spent"] == 360_000
    assert data["remaining"] == -360_000
    assert data["overall_balance"] == 140_000
    assert data["daily_average"] == round(360_000 / max(1, user_timezone_today().day))


def test_dashboard_summary_net_position_counts_payment_plan_once(client, session):
    email = "summaryplanonce@example.com"
    headers = create_user_and_token(client, "summaryplanonce", email, "Password123!")
    onboard = client.post(
        "/users/me/onboarding",
        json={
            "life_statuses": ["employed"],
            "wallets": [{"name": "Cash", "initial_balance": 1_000_000}],
        },
        headers=headers,
    )
    assert onboard.status_code == 200
    user = session.query(models.User).filter(models.User.email == email).one()
    today = user_timezone_today()

    linked_debt = models.Debt(
        owner_id=user.id,
        debt_type=models.DebtType.OWING,
        origin_kind=models.DebtOriginKind.FINANCED_ASSET_PURCHASE,
        counterparty_kind=models.DebtCounterpartyKind.STORE,
        counterparty_name="Legacy store",
        initial_amount=400_000,
        remaining_amount=400_000,
        date=today,
        expected_return_date=today,
    )
    regular_debt = models.Debt(
        owner_id=user.id,
        debt_type=models.DebtType.OWING,
        origin_kind=models.DebtOriginKind.CASH_BORROWED,
        counterparty_kind=models.DebtCounterpartyKind.PERSON,
        counterparty_name="Friend",
        initial_amount=100_000,
        remaining_amount=100_000,
        date=today,
        expected_return_date=today,
    )
    receivable = models.Debt(
        owner_id=user.id,
        debt_type=models.DebtType.OWED,
        origin_kind=models.DebtOriginKind.CASH_LENT,
        counterparty_kind=models.DebtCounterpartyKind.PERSON,
        counterparty_name="Coworker",
        initial_amount=50_000,
        remaining_amount=50_000,
        date=today,
        expected_return_date=today,
    )
    session.add_all([linked_debt, regular_debt, receivable])
    session.flush()
    session.add(
        models.PaymentPlan(
            owner_id=user.id,
            debt_id=linked_debt.id,
            item_name="Phone",
            plan_type=models.PaymentPlanType.STORE_INSTALLMENT,
            total_price=400_000,
            down_payment=0,
            remaining_amount=400_000,
            months=1,
            payment_count=1,
            frequency=models.PaymentPlanFrequency.MONTHLY,
            monthly_payment_amount=400_000,
            regular_payment_amount=400_000,
            status=models.PaymentPlanStatus.ACTIVE,
            start_date=today,
            expense_category=models.ExpenseCategory.ELECTRONICS,
        )
    )
    session.commit()

    res = client.get("/analytics/dashboard-summary", headers=headers)

    assert res.status_code == 200, res.text
    data = res.json()
    assert data["overall_balance"] == 1_000_000
    assert data["net_position"] == 550_000


def test_analytics_spending_excludes_legacy_payment_plan_debt_duplicate(client, session):
    email = "analyticsplanduplicate@example.com"
    headers = create_user_and_token(client, "analyticsplanduplicate", email, "Password123!")
    today = user_timezone_today()
    user = session.query(models.User).filter(models.User.email == email).one()

    debt = models.Debt(
        owner_id=user.id,
        debt_type=models.DebtType.OWING,
        origin_kind=models.DebtOriginKind.FINANCED_ASSET_PURCHASE,
        counterparty_kind=models.DebtCounterpartyKind.STORE,
        counterparty_name="Legacy store",
        initial_amount=200_000,
        remaining_amount=200_000,
        date=today,
        expected_return_date=today,
    )
    session.add(debt)
    session.flush()
    plan = models.PaymentPlan(
        owner_id=user.id,
        debt_id=debt.id,
        item_name="Phone",
        plan_type=models.PaymentPlanType.STORE_INSTALLMENT,
        total_price=200_000,
        down_payment=0,
        remaining_amount=200_000,
        months=1,
        payment_count=1,
        frequency=models.PaymentPlanFrequency.MONTHLY,
        monthly_payment_amount=200_000,
        regular_payment_amount=200_000,
        status=models.PaymentPlanStatus.ACTIVE,
        start_date=today,
        expense_category=models.ExpenseCategory.ELECTRONICS,
    )
    session.add(plan)
    session.flush()
    event = models.FinancialEvent(
        owner_id=user.id,
        title="Legacy duplicated plan payment",
        event_type=models.TransactionType.EXPENSE,
        status=models.FinancialEventStatus.POSTED,
        date=today,
    )
    session.add(event)
    session.flush()
    session.add_all(
        [
            models.EntityLedger(
                event_id=event.id,
                label="Debt leg",
                amount=200_000,
                category=models.ExpenseCategory.ELECTRONICS,
                debt_id=debt.id,
            ),
            models.EntityLedger(
                event_id=event.id,
                label="Payment plan leg",
                amount=200_000,
                category=models.ExpenseCategory.ELECTRONICS,
                payment_plan_id=plan.id,
            ),
        ]
    )
    session.commit()

    summary = client.get("/analytics/dashboard-summary", headers=headers)
    history = client.get("/analytics/history", headers=headers)
    trend = client.get(f"/analytics/daily-trend?start_date={today.isoformat()}&end_date={today.isoformat()}", headers=headers)
    breakdown = client.get(f"/analytics/category-breakdown?start_date={today.isoformat()}&end_date={today.isoformat()}", headers=headers)

    assert summary.status_code == 200, summary.text
    assert history.status_code == 200, history.text
    assert trend.status_code == 200, trend.text
    assert breakdown.status_code == 200, breakdown.text
    assert summary.json()["spent"] == 200_000
    assert history.json()["total_spent_lifetime"] == 200_000
    assert trend.json()[0]["amount"] == 200_000
    assert breakdown.json()[0]["total"] == 200_000
