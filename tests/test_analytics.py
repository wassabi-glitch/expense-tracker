from datetime import date, timedelta
from tests.helpers import create_user_and_token, create_budget, create_expense


def test_analytics_history(client):
    headers = create_user_and_token(
        client, "analyticsuser", "analyticsuser@example.com", "Password123!"
    )
    create_budget(client, headers, category="Food", monthly_limit=500)

    # Add two expenses directly (same day = same month as budget, always safe)
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

    today = date.today()
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

    today = date.today()
    # Use a date that stays within the same month
    safe_date = today.replace(day=max(1, today.day - 3)) if today.day > 3 else today
    # Create budget for the expense's month if different from today
    if safe_date.month != today.month or safe_date.year != today.year:
        create_budget(client, headers, category="Food", monthly_limit=500,
                      budget_year=safe_date.year, budget_month=safe_date.month)

    create_expense(client, headers, title="Three Days", amount=10, category="Food",
                   expense_date=safe_date)

    res = client.get("/analytics/daily-trend?days=2", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert len(data) == 2


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

    today = date.today()
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

    today = date.today()
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

    today = date.today()
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
